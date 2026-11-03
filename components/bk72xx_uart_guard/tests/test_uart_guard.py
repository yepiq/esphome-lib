"""Exercise the real read guard with deterministic IRQ and serial doubles."""
import asyncio
import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile

from esphome.core import CORE

ROOT = Path(__file__).resolve().parents[1]
STUBS = {
    'Arduino.h': '''#pragma once
#define LT_ARD_HAS_SERIAL 1
''',
    'Serial.h': '''#pragma once
#include <cstdint>
extern void inject_interrupt();
struct SerialClass {
  uint8_t data[256]{}; int head=0,tail=0,count=0;
  int available(){return count;}
  void store(int ch){if(count==256)return;data[head]=ch;head=(head+1)%256;++count;}
  int read_raw(){if(!count)return -1;int ch=data[tail];tail=(tail+1)%256;
    int before=count;inject_interrupt();count=before-1;return ch;}
  void clear(){head=tail=count=0;}
};
inline SerialClass Serial1,Serial2;
''',
    'esphome/core/defines.h': '#pragma once\n',
}

SOURCE = r'''
#include <cassert>
#include <cstdint>
#include <initializer_list>
#include "bk72xx_uart_guard.cpp"
using namespace esphome::bk72xx_uart_guard;
uint32_t cpsr=0x13;
bool inject=false,pending_interrupt=false;
uint32_t interrupt_mask=0x80;
SerialClass*active=&Serial1;
void deliver(){for(int i=0;i<20;++i)active->store(30+i);}
void inject_interrupt(){if(!inject)return;inject=false;if(cpsr&interrupt_mask)pending_interrupt=true;else deliver();}
namespace esphome::bk72xx_uart_guard {
uint32_t save_and_mask_irq_fiq(){uint32_t old=cpsr;cpsr|=0xc0;return old;}
void restore_irq_fiq(uint32_t old){cpsr=(cpsr&~0xc0U)|(old&0xc0U);
 if(pending_interrupt&&!(cpsr&interrupt_mask)){pending_interrupt=false;deliver();}}
}
extern "C" int __real__ZN11SerialClass4readEv(SerialClass*self){return self->read_raw();}
int main(){
 // The unguarded control loses 20 ISR increments at the exact read/modify/write window.
 Serial1.store(11);Serial1.store(22);inject=true;
 assert(Serial1.read_raw()==11);assert(Serial1.count==1);assert((Serial1.head-Serial1.tail+256)%256==21);
 for(auto*port:{&Serial1,&Serial2})for(uint32_t masks:{0U,0x40U,0x80U,0xc0U})for(uint32_t irq:{0x40U,0x80U}){
   active=port;port->clear();port->store(11);port->store(22);cpsr=0x13|masks;interrupt_mask=irq;inject=true;pending_interrupt=false;
   assert(__wrap__ZN11SerialClass4readEv(port)==11);assert(cpsr==(0x13|masks));
   assert((port->head-port->tail+256)%256==port->count);
   cpsr=0x13;if(pending_interrupt){pending_interrupt=false;deliver();}
   assert(port->count==21);assert(__wrap__ZN11SerialClass4readEv(port)==22);
   for(int i=0;i<20;++i)assert(__wrap__ZN11SerialClass4readEv(port)==30+i);
   assert(__wrap__ZN11SerialClass4readEv(port)==-1);
 }
 // Full rings discard new bytes; guarded reads preserve FIFO order across wrapping.
 cpsr=0x13;
 for(auto*port:{&Serial1,&Serial2}){
   port->clear();assert(__wrap__ZN11SerialClass4readEv(port)==-1);
   for(int cycle=0;cycle<3;++cycle){
     for(int i=0;i<256;++i)port->store(i);
     port->store(37);assert(port->available()==256);
     for(int i=0;i<256;++i)assert(__wrap__ZN11SerialClass4readEv(port)==i);
     assert(__wrap__ZN11SerialClass4readEv(port)==-1);
   }
   for(int i=0;i<513;++i){port->store(i%256);assert(__wrap__ZN11SerialClass4readEv(port)==i%256);}
   assert(port->available()==0);
 }
}
'''


def test_source_gating():
    spec = importlib.util.spec_from_file_location('tested_uart_guard', ROOT / '__init__.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for has_uart in (False, True):
        CORE.reset()
        CORE.config = {'uart': [{'id': 'test_uart'}]} if has_uart else {}
        asyncio.run(module.to_code({}))
        expected_flags = {'-Wl,--wrap=_ZN11SerialClass4readEv'} if has_uart else set()
        assert CORE.build_flags == expected_flags
        excluded = module.FILTER_SOURCE_FILES()
        for source in ('bk72xx_uart_guard.cpp', 'bk72xx_uart_guard.h'):
            assert (source not in excluded) == has_uart
    print('PASS: merged UART presence gates the wrapper flag and all guard sources', flush=True)


if __name__ == '__main__':
    test_source_gating()
    with tempfile.TemporaryDirectory(prefix='bk72xx-uart-test-') as directory:
        root = Path(directory)
        for name, source in STUBS.items():
            p = root / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(source)
        (root / 'test.cpp').write_text(SOURCE)
        for optimization in ('-O0', '-O2'):
            binary = root / ('test' + optimization)
            subprocess.run([os.environ.get('CXX', 'clang++'), '-std=c++17', optimization,
                            '-DUSE_HOST', '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                            '-I' + str(root), '-I' + str(ROOT), str(root / 'test.cpp'), '-o', str(binary)], check=True)
            subprocess.run([str(binary)], check=True)
            print(f'PASS {optimization}: real wrapper, IRQ/FIQ masks, both ports, FIFO boundaries', flush=True)

"""Exercise the real guard/sensor with deterministic IRQ, serial and flash doubles."""
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
#define LT_HW_UART1 1
#define LT_HW_UART2 1
#define LT_SERIAL_BUFFER_SIZE 256
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
    'esphome/core/defines.h': '#pragma once\n#define USE_BK72XX_UART_OVERFLOW_SENSOR\n',
    'esphome/core/component.h': '''#pragma once
#include <cstdint>
namespace esphome {
namespace setup_priority {constexpr float DATA=600;}
class PollingComponent {bool failed_=false;public:virtual ~PollingComponent()=default;
 virtual void setup(){};virtual void dump_config(){};virtual void update(){};virtual void on_shutdown(){};
 virtual float get_setup_priority()const{return 0;}
 void mark_failed(){failed_=true;}bool is_failed()const{return failed_;}};
}
''',
    'esphome/core/log.h': '''#pragma once
#define ESP_LOGE(...) ((void)0)
#define ESP_LOGW(...) ((void)0)
#define ESP_LOGCONFIG(...) ((void)0)
#define LOG_SENSOR(...) ((void)0)
#define LOG_UPDATE_INTERVAL(...) ((void)0)
''',
    'esphome/core/helpers.h': '''#pragma once
#include <cstdint>
namespace esphome {inline uint32_t fnv1_hash(const char*s){uint32_t h=2166136261U;while(*s){h*=16777619U;h^=*s++;}return h;}}
''',
    'esphome/core/preferences.h': '''#pragma once
#include <cassert>
#include <cstdint>
#include <map>
extern bool in_isr;
namespace esphome {
inline std::map<uint32_t,uint32_t> flash,pending;
inline bool fail_save=false;inline unsigned saves=0,syncs=0;
class ESPPreferenceObject {uint32_t key_=0;public:
 ESPPreferenceObject()=default;explicit ESPPreferenceObject(uint32_t key):key_(key){}
 bool load(uint32_t*p){assert(!in_isr);if(!flash.count(key_))return false;*p=flash[key_];return true;}
 bool save(const uint32_t*p){assert(!in_isr);++saves;if(fail_save)return false;pending[key_]=*p;return true;}
};
struct ESPPreferences {
 template<typename T>ESPPreferenceObject make_preference(uint32_t key){static_assert(sizeof(T)==4);return ESPPreferenceObject(key);}
 bool sync(){assert(!in_isr);++syncs;for(auto [k,v]:pending)flash[k]=v;pending.clear();return true;}
};
inline ESPPreferences preferences;inline auto*global_preferences=&preferences;
}
''',
    'esphome/components/sensor/sensor.h': '''#pragma once
#include <cassert>
extern bool in_isr;
namespace esphome::sensor {class Sensor {bool valid_=false;public:float state=0;unsigned publishes=0;
 bool has_state()const{return valid_;}void publish_state(float value){assert(!in_isr);valid_=true;state=value;++publishes;}};}
''',
    'esphome/components/uart/uart.h': '''#pragma once
namespace esphome::uart {
class UARTComponent {};
class UARTDevice {protected:UARTComponent*parent_=nullptr;public:void set_uart_parent(UARTComponent*p){parent_=p;}};
}
''',
    'esphome/components/uart/uart_component_libretiny.h': '''#pragma once
#include "uart.h"
namespace esphome::uart {
class LibreTinyUARTComponent:public UARTComponent {int index_;public:explicit LibreTinyUARTComponent(int index):index_(index){} int get_hw_serial_number(){return index_;}};
}
''',
}

SOURCE = r'''
#include <cassert>
#include <cstdint>
#include <initializer_list>
#include "bk72xx_uart_guard.cpp"
#include "uart_overflow_sensor.cpp"
using namespace esphome;
using namespace esphome::bk72xx_uart_guard;
uint32_t cpsr=0x13;
bool in_isr=false,inject=false,pending_interrupt=false;
uint32_t interrupt_mask=0x80;
SerialClass*active=&Serial1;
int incoming=-1;unsigned real_reads=0;
void deliver(){in_isr=true;for(int i=0;i<20;++i)active->store(30+i);in_isr=false;}
void inject_interrupt(){if(!inject)return;inject=false;if(cpsr&interrupt_mask)pending_interrupt=true;else deliver();}
namespace esphome::bk72xx_uart_guard {
uint32_t save_and_mask_irq_fiq(){uint32_t old=cpsr;cpsr|=0xc0;return old;}
void restore_irq_fiq(uint32_t old){cpsr=(cpsr&~0xc0U)|(old&0xc0U);
 if(pending_interrupt&&!(cpsr&interrupt_mask)){pending_interrupt=false;deliver();}}
}
extern "C" int __real__ZN11SerialClass4readEv(SerialClass*self){return self->read_raw();}
extern "C" int __real_uart_read_byte(int){++real_reads;return incoming;}
void receive(int port,int byte){incoming=byte;in_isr=true;int ch=__wrap_uart_read_byte(port);
 assert(ch==byte);if(ch>=0&&port>=0&&port<2)(port==0?Serial1:Serial2).store(ch);in_isr=false;}
void full(int port){auto&b=port==0?Serial1:Serial2;b.clear();for(int i=0;i<256;++i)receive(port,i);}
void reset_bss(){Serial1.clear();Serial2.clear();overflow_count[0]=overflow_count[1]=0;monitors[0]=monitors[1]=nullptr;pending.clear();}
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
 active=&Serial1;cpsr=0x13;
 // Empty, full, wraparound and other-port/negative-sentinel handling.
 reset_bss();full(0);assert(overflow_count[0]==0);
 receive(0,0);receive(0,255);receive(0,37);receive(0,-1);receive(99,42);
 assert(overflow_count[0]==3&&overflow_count[1]==0);
 for(int i=0;i<256;++i)assert(__wrap__ZN11SerialClass4readEv(&Serial1)==i);
 for(int cycle=0;cycle<3;++cycle){full(0);for(int i=0;i<256;++i)assert(__wrap__ZN11SerialClass4readEv(&Serial1)==i);}
 uart::LibreTinyUARTComponent bus1(1),bus2(2),invalid(-1);
 UARTOverflowSensor a;a.set_uart_parent(&bus1);a.setup();assert(a.state==3);assert(flash.empty());
 unsigned published=a.publishes,saved=saves;a.update();assert(a.publishes==published&&saves==saved);
 full(0);receive(0,1);receive(0,2);a.update();assert(a.state==5);assert(flash.empty());
 full(1);receive(1,7);receive(1,8);
 UARTOverflowSensor b;b.set_uart_parent(&bus2);b.setup();assert(b.state==2&&a.state==5);
 UARTOverflowSensor duplicate;duplicate.set_uart_parent(&bus1);duplicate.setup();assert(duplicate.is_failed());
 UARTOverflowSensor wrong;wrong.set_uart_parent(&invalid);wrong.setup();assert(wrong.is_failed());
 // Shutdown catches events since the last poll and flushes both independent preference keys.
 receive(0,3);a.on_shutdown();assert(a.state==6&&flash.size()==2&&pending.empty());
 // Reboot/reflash: flash survives, RAM resets, and new startup drops are added once.
 reset_bss();full(0);receive(0,1);receive(0,2);
 UARTOverflowSensor renamed;renamed.set_uart_parent(&bus1);renamed.setup();assert(renamed.state==8);
 UARTOverflowSensor port2;port2.set_uart_parent(&bus2);port2.setup();assert(port2.state==2);
 renamed.on_shutdown();reset_bss();
 UARTOverflowSensor reflashed;reflashed.set_uart_parent(&bus1);reflashed.setup();assert(reflashed.state==8);
 // A failed preference enqueue is retried without requiring another overflow.
 full(0);receive(0,1);fail_save=true;reflashed.update();assert(reflashed.state==9);
 fail_save=false;reflashed.update();assert(!pending.empty());
 // Sudden power loss can lose an unsynced increment under ordinary ESPHome batching.
 reset_bss();UARTOverflowSensor power_loss;power_loss.set_uart_parent(&bus1);power_loss.setup();assert(power_loss.state==8);
 assert(real_reads>0);
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
        assert ('-Wl,--wrap=_ZN11SerialClass4readEv' in CORE.build_flags) == has_uart
        excluded = module.FILTER_SOURCE_FILES()
        assert ('bk72xx_uart_guard.cpp' not in excluded) == has_uart
        assert 'uart_overflow_sensor.cpp' in excluded
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
            print(f'PASS {optimization}: real wrapper, IRQ/FIQ masks, both ports, overflow, preference restoration', flush=True)

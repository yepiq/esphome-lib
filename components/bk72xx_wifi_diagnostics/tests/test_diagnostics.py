"""Run the real receive wrapper, journal and restart code with bounded SDK doubles."""

import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
STUBS = {
    "esphome/core/component.h": r'''#pragma once
#include <cstdint>
#include <functional>
#include <string>
inline uint32_t test_now=0;
inline uint32_t millis(){return test_now;}
namespace esphome {
namespace setup_priority { constexpr float WIFI=250; }
class PollingComponent {
 public:
  virtual ~PollingComponent()=default;
  virtual void setup(){} virtual void loop(){} virtual void update(){}
  virtual void dump_config(){} virtual void on_shutdown(){}
  virtual float get_setup_priority() const {return 0;}
  void mark_failed(){failed=true;} bool is_failed()const{return failed;}
  void set_timeout(const char*,uint32_t ms,std::function<void()> cb){timeout=ms;timer=cb;}
  bool failed=false; uint32_t timeout=0; std::function<void()> timer;
};
}
''',
    "esphome/core/preferences.h": r'''#pragma once
#include <vector>
#include <cstring>
namespace esphome {
inline std::vector<uint8_t> flash,pending;
struct ESPPreferenceObject {
 template<class T>bool load(T*v){if(flash.size()!=sizeof(T))return false;std::memcpy(v,flash.data(),sizeof(T));return true;}
 template<class T>bool save(const T*v){pending.assign(reinterpret_cast<const uint8_t*>(v),reinterpret_cast<const uint8_t*>(v)+sizeof(T));return true;}
};
struct Preferences {
 unsigned syncs=0;
 template<class T>ESPPreferenceObject make_preference(uint32_t){return {};}
 bool sync(){++syncs;flash=pending;return true;}
};
inline Preferences prefs;inline Preferences*global_preferences=&prefs;
}
''',
    "esphome/core/log.h": r'''#pragma once
#define ESP_LOGW(...) ((void)0)
#define ESP_LOGI(...) ((void)0)
#define ESP_LOGCONFIG(...) ((void)0)
''',
    "esphome/components/sensor/sensor.h": r'''#pragma once
namespace esphome::sensor { struct Sensor {float state{};void publish_state(float v){state=v;}}; }
''',
    "esphome/components/text_sensor/text_sensor.h": r'''#pragma once
#include <string>
namespace esphome::text_sensor { struct TextSensor {std::string state;void publish_state(const std::string&v){state=v;}}; }
''',
    "esphome/components/wifi/wifi_component.h": r'''#pragma once
#include <functional>
namespace esphome::wifi {
struct WiFiComponent {
 bool disabled=false;unsigned enables=0,disables=0;std::function<void()> check_armed;
 bool is_disabled()const{return disabled;}
 void disable(){if(check_armed)check_armed();disabled=true;++disables;}
 void enable(){disabled=false;++enables;}
};
inline WiFiComponent fake_wifi;inline WiFiComponent*global_wifi_component=&fake_wifi;
}
''',
    "FreeRTOS.h": '#pragma once\n#define pdTRUE 1\n',
    "queue.h": r'''#pragma once
#include <deque>
#include <vector>
#include <cstring>
struct Queue {size_t capacity,size;std::deque<std::vector<unsigned char>>data;};
using QueueHandle_t=Queue*;
inline QueueHandle_t xQueueCreate(size_t n,size_t size){return new Queue{n,size,{}};}
inline int xQueueSend(QueueHandle_t q,const void*p,int){if(q->data.size()==q->capacity)return 0;
 auto b=static_cast<const unsigned char*>(p);q->data.emplace_back(b,b+q->size);return 1;}
inline int xQueueReceive(QueueHandle_t q,void*p,int){if(q->data.empty())return 0;
 std::memcpy(p,q->data.front().data(),q->size);q->data.pop_front();return 1;}
''',
    "WiFi.h": r'''#pragma once
#include <functional>
#include <cstdint>
enum WiFiEvent_t {ARDUINO_EVENT_WIFI_STA_START,ARDUINO_EVENT_WIFI_STA_STOP,
 ARDUINO_EVENT_WIFI_STA_CONNECTED,ARDUINO_EVENT_WIFI_STA_DISCONNECTED,ARDUINO_EVENT_WIFI_STA_GOT_IP};
struct WiFiEventInfo_t {struct {uint8_t reason;}wifi_sta_disconnected;};
struct WiFiClass {
 std::function<void(WiFiEvent_t,WiFiEventInfo_t)> callback;bool sleep=false;
 void onEvent(std::function<void(WiFiEvent_t,WiFiEventInfo_t)>cb){callback=cb;}
 bool getSleep()const{return sleep;}
 void emit(WiFiEvent_t event,uint8_t reason=0){callback(event,{{reason}});}
};
inline WiFiClass WiFi;
''',
    "lwip/pbuf.h": r'''#pragma once
#include <algorithm>
#include <cstring>
#include <cstdint>
struct pbuf {void*payload;uint16_t len;pbuf*next;};
inline uint16_t pbuf_copy_partial(const pbuf*p,void*out,uint16_t len,uint16_t offset){
 uint16_t copied=0;auto*dst=static_cast<uint8_t*>(out);
 for(;p&&copied<len;p=p->next){if(offset>=p->len){offset-=p->len;continue;}
  auto n=std::min<uint16_t>(len-copied,p->len-offset);std::memcpy(dst+copied,static_cast<uint8_t*>(p->payload)+offset,n);copied+=n;offset=0;}
 return copied;
}
''',
}

SOURCE = r'''
#include <cassert>
#include <limits>
#include "bk72xx_wifi_diagnostics.cpp"
using namespace esphome;
using namespace esphome::bk72xx_wifi_diagnostics;
struct netif {int id;};
netif station{0},ap{1};unsigned forwards=0;int forwarded_iface=-1;pbuf*forwarded=nullptr;
extern "C" netif*rwm_mgmt_get_vif2netif(uint8_t iface){return iface==0?&station:&ap;}
extern "C" void*net_get_sta_handle(){return &station;}
extern "C" void __real_ethernetif_input(int iface,pbuf*p){++forwards;forwarded_iface=iface;forwarded=p;}
struct Diagnostics:WiFiDiagnostics {
 sensor::Sensor sensors[6];text_sensor::TextSensor history,snapshot_text;
 Diagnostics(){for(size_t i=0;i<6;i++)set_counter(i,&sensors[i]);set_event_history(&history);set_rx_snapshot(&snapshot_text);}
 ~Diagnostics(){delete events_;}
 const DiagnosticState&state()const{return state_;}
 void simulate_wrap(){collected_[0]=UINT32_MAX;received_[0].store(2);}
};
void frame(int iface,uint16_t type,bool group,bool split=false){
 uint8_t header[14]{};header[0]=group?0xff:0x02;header[12]=type>>8;header[13]=type;
 pbuf tail{header+5,9,nullptr};pbuf packet{header,uint16_t(split?5:14),split?&tail:nullptr};
 auto before=forwards;__wrap_ethernetif_input(iface,&packet);
 assert(forwards==before+1&&forwarded==&packet&&forwarded_iface==iface);
 assert(packet.len==(split?5:14));
}
int main(){
 {
 Diagnostics d;d.setup();assert(d.state().boots==1);auto writes=prefs.syncs;
 for(uint16_t type:{0x0800,0x0806,0x888e})for(bool group:{false,true}){
  frame(0,type,group,true);frame(1,type,group); // AP traffic must be ignored
 }
 frame(0,0x86dd,false); // IPv6 is not one of the measured protocols
 uint8_t short_header[5]{};pbuf short_packet{short_header,5,nullptr};
 __wrap_ethernetif_input(0,&short_packet);__wrap_ethernetif_input(0,nullptr);
 assert(prefs.syncs==writes);d.update();assert(prefs.syncs==writes);
 for(auto value:d.state().packets)assert(value==1);
 assert(d.snapshot_text.state.find("ipv4=1/1 arp=1/1 eapol=1/1")!=std::string::npos);
 // Events are copied from the Wi-Fi task, persisted only when the main loop drains.
 test_now=8000;WiFi.emit(ARDUINO_EVENT_WIFI_STA_DISCONNECTED,8);
 assert(prefs.syncs==writes);d.loop();assert(prefs.syncs==writes+1);
 assert(d.history.state.find("b1+8s down:8")!=std::string::npos);
 for(int i=0;i<20;i++)WiFi.emit(ARDUINO_EVENT_WIFI_STA_CONNECTED);
 d.loop();assert(d.history.state.find("lost:4")!=std::string::npos);
 assert(d.state().history_count==HISTORY_SIZE);
 // Timed checkpoint and exact wraparound extension into the persisted uint64 total.
 d.simulate_wrap();test_now+=300000;writes=prefs.syncs;d.update();
 assert(d.state().packets[0]==4);assert(prefs.syncs==writes+1);
 // Arm the timer before disable, reject duplicate requests, recover without a client.
 wifi::fake_wifi.check_armed=[&](){assert(d.timer&&d.timeout==5000);};
 d.restart_wifi();d.restart_wifi();assert(wifi::fake_wifi.disables==1);
 d.timer();assert(!wifi::fake_wifi.disabled&&wifi::fake_wifi.enables==1);
 test_now=UINT32_MAX;d.on_shutdown();assert(d.history.state.size()<255);
 }
 // Reboot/reflash: new component instance loads the same fixed preference record.
 test_now=0;WiFi.callback={};wifi::fake_wifi.check_armed={};
 {
 Diagnostics d;d.setup();d.update();assert(d.state().boots==2);assert(d.state().packets[0]==4);
 assert(d.history.state.find("shutdown")!=std::string::npos);
 assert(d.history.state.find("b2+0s boot")!=std::string::npos);
 frame(0,0x0800,false);d.on_shutdown();assert(d.state().packets[0]==5);
 }
 // Invalid persisted schema must not expose invalid ring indices or random counters.
 flash[0]=0xff;
 {Diagnostics d;d.setup();d.update();assert(d.state().boots==1);assert(d.state().packets[0]==0);}
 assert(classify_frame(nullptr,0)==-1);
 assert(counter_delta(2,UINT32_MAX)==3);
}
'''

if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="bk72xx-wifi-test-") as directory:
        root = Path(directory)
        for name, source in STUBS.items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(source)
        (root / "test.cpp").write_text(SOURCE)
        for optimization in ("-O0", "-O2"):
            binary = root / ("test" + optimization)
            subprocess.run([os.environ.get("CXX", "clang++"), "-std=c++17", optimization,
                            "-fsanitize=address,undefined", "-fno-omit-frame-pointer",
                            "-I" + str(root), "-I" + str(ROOT), str(root / "test.cpp"), "-o", str(binary)], check=True)
            subprocess.run([str(binary)], check=True)
            print(f"PASS {optimization}: forwarding, split packets, interface filtering, persistence, events, restart", flush=True)

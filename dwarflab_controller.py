import struct, uuid, threading, time, logging, requests, websocket
log = logging.getLogger("dwarflab")
MODULE_NONE=0;MODULE_CAMERA_TELE=1;MODULE_CAMERA_WIDE=2;MODULE_ASTRO=3
MODULE_SYSTEM=4;MODULE_RGB_POWER=5;MODULE_MOTOR=6;MODULE_TRACK=7
MODULE_FOCUS=8;MODULE_NOTIFY=9;MODULE_PANORAMA=10;MODULE_ITIPS=11
MODULE_TEST=12;MODULE_SHOOTING_SCHEDULE=13;MODULE_TASK_CENTER=14;MODULE_PARAM=15
def _module_for_cmd(c):
    if 10000<=c<10500: return MODULE_CAMERA_TELE
    if 11000<=c<11500: return MODULE_ASTRO
    if 12000<=c<12500: return MODULE_CAMERA_WIDE
    if 13000<=c<13300: return MODULE_SYSTEM
    if 13500<=c<13800: return MODULE_RGB_POWER
    if 14000<=c<14500: return MODULE_MOTOR
    if 14800<=c<14900: return MODULE_TRACK
    if 15000<=c<15200: return MODULE_FOCUS
    if 15200<=c<15500: return MODULE_NOTIFY
    if 15500<=c<15600: return MODULE_PANORAMA
    if 15700<=c<15800: return MODULE_ITIPS
    if 16100<=c<16400: return MODULE_SHOOTING_SCHEDULE
    if 16400<=c<16600: return MODULE_TASK_CENTER
    if 16700<=c<16800: return MODULE_PARAM
    return MODULE_NONE
MSG_TYPE_REQUEST=0;MSG_TYPE_RESPONSE=1
CMD_CAMERA_TELE_OPEN_CAMERA=10000;CMD_CAMERA_TELE_CLOSE_CAMERA=10001
CMD_CAMERA_TELE_PHOTOGRAPH=10002;CMD_CAMERA_TELE_BURST=10003
CMD_CAMERA_TELE_STOP_BURST=10004;CMD_CAMERA_TELE_START_RECORD=10005
CMD_CAMERA_TELE_STOP_RECORD=10006;CMD_CAMERA_TELE_SET_EXP=10009
CMD_CAMERA_TELE_SET_GAIN=10013;CMD_CAMERA_TELE_SET_BRIGHTNESS=10015
CMD_CAMERA_TELE_SET_CONTRAST=10017;CMD_CAMERA_TELE_SET_SATURATION=10019
CMD_CAMERA_TELE_SET_SHARPNESS=10023;CMD_CAMERA_TELE_SET_WB_MODE=10025
CMD_CAMERA_TELE_SET_WB_CT=10029;CMD_CAMERA_TELE_SET_IRCUT=10031
CMD_CAMERA_TELE_START_TIMELAPSE_PHOTO=10033;CMD_CAMERA_TELE_STOP_TIMELAPSE_PHOTO=10034
CMD_CAMERA_TELE_GET_ALL_PARAMS=10036;CMD_CAMERA_TELE_SET_JPG_QUALITY=10040
CMD_CAMERA_TELE_PHOTO_RAW=10041;CMD_CAMERA_TELE_SWITCH_RESOLUTION=10047
CMD_CAMERA_TELE_SWITCH_FRAMERATE=10048
CMD_ASTRO_START_CALIBRATION=11000;CMD_ASTRO_STOP_CALIBRATION=11001
CMD_ASTRO_START_GOTO_DSO=11002;CMD_ASTRO_START_GOTO_SOLAR_SYSTEM=11003
CMD_ASTRO_STOP_GOTO=11004;CMD_ASTRO_START_CAPTURE_RAW_LIVE_STACKING=11005
CMD_ASTRO_STOP_CAPTURE_RAW_LIVE_STACKING=11006
CMD_ASTRO_GO_LIVE=11010;CMD_ASTRO_START_ONE_CLICK_GOTO_DSO=11013
CMD_ASTRO_STOP_ONE_CLICK_GOTO=11015
CMD_ASTRO_START_EQ_SOLVING=11018;CMD_ASTRO_STOP_EQ_SOLVING=11019
CMD_ASTRO_START_AI_ENHANCE=11029;CMD_ASTRO_STOP_AI_ENHANCE=11030
CMD_ASTRO_START_ONE_CLICK_SHOOTING=11042
CMD_ASTRO_START_SKY_TARGET_FINDER=11047;CMD_ASTRO_STOP_SKY_TARGET_FINDER=11048
CMD_SYSTEM_SET_TIME=13000;CMD_SYSTEM_SET_LOCATION=13010
CMD_RGB_POWER_POWER_DOWN=13502;CMD_RGB_POWER_POWERIND_ON=13503
CMD_RGB_POWER_POWERIND_OFF=13504;CMD_RGB_POWER_REBOOT=13505
CMD_STEP_MOTOR_JOYSTICK=14006      # CMD_STEP_MOTOR_SERVICE_JOYSTICK in APK
CMD_STEP_MOTOR_JOYSTICK_STOP=14008  # CMD_STEP_MOTOR_SERVICE_JOYSTICK_STOP in APK
CMD_TRACK_START_TRACK=14800;CMD_TRACK_STOP_TRACK=14801
CMD_FOCUS_AUTO_FOCUS=15000;CMD_FOCUS_MANUAL_SINGLE_STEP=15001
CMD_FOCUS_START_MANUAL_CONTINUOUS=15002;CMD_FOCUS_STOP_MANUAL_CONTINUOUS=15003
CMD_FOCUS_START_ASTRO_AUTO_FOCUS=15004;CMD_FOCUS_STOP_ASTRO_AUTO_FOCUS=15005
CMD_GLOBAL_TASK_MANAGER_ENTER_CAMERA=16404
CMD_GLOBAL_TASK_GET_DEVICE_STATE_INFO=16405
CMD_CAMERA_WIDE_OPEN_CAMERA=12000
CMD_ASTRO_WIDE_GO_LIVE=11019
CMD_NOTIFY_ELE=15201;CMD_NOTIFY_ELE_STATUS=15202;CMD_NOTIFY_TEMPERATURES=15203
CMD_NOTIFY_TEMPERATURE=15243;CMD_NOTIFY_FOCUS_POSITION=15257
CMD_NOTIFY_CMOS_TEMPERATURE=15292;CMD_NOTIFY_STATE_ASTRO_CALIBRATION=15210
CMD_NOTIFY_STATE_ASTRO_GOTO=15211;CMD_NOTIFY_STATE_ASTRO_TRACKING=15212
CMD_NOTIFY_STATE_CAPTURE_RAW_LIVE_STACKING=15208
CMD_NOTIFY_PROGRASS_CAPTURE_RAW_LIVE_STACKING=15209
def _varint(v):
    v=v&0xFFFFFFFFFFFFFFFF  # treat negatives as uint64 two's-complement (protobuf wire format)
    b=[]
    while True:
        b.append(v&0x7F);v>>=7
        if v==0:break
    for i in range(len(b)-1):b[i]|=0x80
    return bytes(b)
def _field(fn,wt,val):
    tag=_varint((fn<<3)|wt)
    if wt==0:return tag+_varint(val)
    if wt==1:return tag+struct.pack("<d",val)
    if wt==2:
        if isinstance(val,str):val=val.encode()
        return tag+_varint(len(val))+val
    raise ValueError(f"bad wt {wt}")
def _dvarint(buf,pos):
    r=0;s=0
    while True:
        b=buf[pos];pos+=1;r|=(b&0x7F)<<s
        if not(b&0x80):break
        s+=7
    return r,pos
def build_ws_packet(cmd,data=b"",device_id=1,client_id=""):
    mid=_module_for_cmd(cmd)
    pkt=(_field(1,0,1)+_field(2,0,20)+_field(3,0,device_id)+_field(4,0,mid)+_field(5,0,cmd)+_field(6,0,0))
    if data:pkt+=_field(7,2,data)
    if client_id:pkt+=_field(8,2,client_id)
    return pkt
def parse_ws_packet(raw):
    r={"major_version":0,"minor_version":0,"device_id":0,"module_id":0,"cmd":0,"type":0,"data":b"","client_id":""}
    i=0
    while i<len(raw):
        try:
            tag,i=_dvarint(raw,i)   # _dvarint returns (value, new_pos)
            fn=tag>>3;wt=tag&7
            if wt==0:
                v,i=_dvarint(raw,i)
                k={1:"major_version",2:"minor_version",3:"device_id",4:"module_id",5:"cmd",6:"type"}.get(fn)
                if k:r[k]=v
            elif wt==2:
                ln,i=_dvarint(raw,i)
                pay=raw[i:i+ln];i+=ln
                if fn==7:r["data"]=pay
                elif fn==8:r["client_id"]=pay.decode("utf-8","replace")
            elif wt==1:i+=8
            elif wt==5:i+=4
            else:break
        except:break
    return r
def p_int(v):return _field(1,0,v) if v!=0 else b""
def p_goto_dso(ra,dec,name=""):
    d=_field(1,1,ra)+_field(2,1,dec)
    if name:d+=_field(3,2,name)
    return d
def p_location(lat,lon,alt=0.0):return _field(1,1,lat)+_field(2,1,lon)+_field(3,1,alt)
def p_joystick(vector_angle_deg, vector_length):
    """
    Build ReqMotorServiceJoystick payload.
    vector_angle_deg : float, degrees clockwise from North (0=N, 90=E, 180=S, 270=W)
                       Internally stored as standard math angle: 0=East, 90=North.
                       The app computes: degrees = toDegrees(atan2(-cy, cx)) normalised 0-360.
    vector_length    : float 0.0-1.0, proportion of max joystick displacement.
    Both fields use proto wire type 1 (64-bit double / fixed64).
    """
    # field 1 = vector_angle (double), field 2 = vector_length (double)
    return _field(1, 1, float(vector_angle_deg)) + _field(2, 1, float(vector_length))

def xy_to_polar(x, y):
    """
    Convert cartesian joystick x/y (-100..100) to (vector_angle_deg, vector_length).
    Matches PolarDpadJoystickView.l(): angle = toDegrees(atan2(-cy, cx)), 0-360.
    x positive = East, y positive = North (screen y is inverted in the app).
    """
    import math
    if x == 0 and y == 0:
        return 0.0, 0.0
    # App uses screen coords where cy increases downward, so North = -cy
    # We receive y positive = North, so pass cy = -y to match app convention
    angle = math.degrees(math.atan2(y, x))   # standard math: 0=E, 90=N
    if angle < 0:
        angle += 360.0
    length = min(1.0, math.hypot(x, y) / 100.0)
    return angle, length
class DwarfLab:
    DEFAULT_IP="192.168.88.1";WS_PORT=9900;HTTP_PORT=8082
    def __init__(self,host=DEFAULT_IP,device_id=1,on_notify=None):
        self.host=host;self.device_id=device_id;self.client_id=str(uuid.uuid4())
        self._ws=None;self._ws_thread=None;self._connected=threading.Event()
        self.on_notify=on_notify
        self.state={"connected":False,"battery":None,"temperature":None,"cmos_temp":None,
                    "goto_state":None,"tracking":False,"stacking":False,"stacking_progress":0,
                    "calibrating":False,"focus_position":None,"last_cmd":None}
    def _ws_url(self):
        return f"ws://{self.host}:{self.WS_PORT}/?client_id={self.client_id}"

    def _start_ws(self):
        """Create and start a websocket connection in a daemon thread."""
        self._ws=websocket.WebSocketApp(
            self._ws_url(),
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close
        )
        t=threading.Thread(target=self._ws.run_forever,
                           kwargs={"ping_interval":20,"ping_timeout":10},
                           daemon=True)
        t.start()
        return t

    def connect(self,timeout=10.0):
        self._ws_thread=self._start_ws()
        ok=self._connected.wait(timeout)
        if ok:self.state["connected"]=True
        # Start reconnect watchdog
        threading.Thread(target=self._reconnect_loop,daemon=True).start()
        return ok

    def _reconnect_loop(self):
        """Background thread: reconnects if WS drops."""
        import time
        while True:
            time.sleep(5)
            if not self._connected.is_set():
                log.warning("WS disconnected — reconnecting...")
                self.state["connected"]=False
                try:
                    if self._ws:
                        self._ws.close()
                except Exception:
                    pass
                self._connected.clear()
                self._ws_thread=self._start_ws()
                ok=self._connected.wait(10)
                if ok:
                    log.info("WS reconnected")
                    self.state["connected"]=True
                else:
                    log.warning("WS reconnect failed, will retry...")
    def disconnect(self):
        if self._ws:self._ws.close()
        self._connected.clear();self.state["connected"]=False
    def _on_open(self,ws):self._connected.set()
    def _on_message(self,ws,msg):
        if not isinstance(msg,bytes):return
        pkt=parse_ws_packet(msg);cmd=pkt["cmd"]
        data = pkt["data"]
        if cmd==CMD_NOTIFY_ELE:             # 15201 battery %
            try:v,_=_dvarint(data,1);self.state["battery"]=v
            except:pass
        elif cmd==CMD_NOTIFY_ELE_STATUS:    # 15202 battery status (field1=level)
            try:v,_=_dvarint(data,1);self.state["battery"]=v
            except:pass
        elif cmd==CMD_NOTIFY_TEMPERATURES:  # 15203 field1=temp, field2=cmos_temp
            try:
                i=0
                tag,i=_dvarint(data,i);fn1=tag>>3
                v1,i=_dvarint(data,i)
                tag,i=_dvarint(data,i);fn2=tag>>3
                v2,i=_dvarint(data,i)
                self.state["temperature"]=round(v1/10.0,1)
                self.state["cmos_temp"]=round(v2/10.0,1)
            except:pass
        elif cmd==CMD_NOTIFY_TEMPERATURE:   # 15243
            try:v,_=_dvarint(data,1);self.state["temperature"]=v
            except:pass
        elif cmd==CMD_NOTIFY_CMOS_TEMPERATURE:  # 15292
            try:v,_=_dvarint(data,1);self.state["cmos_temp"]=v
            except:pass
        elif cmd==CMD_NOTIFY_STATE_ASTRO_GOTO:  # 15211
            try:v,_=_dvarint(data,1);self.state["goto_state"]=v
            except:pass
        elif cmd==CMD_NOTIFY_STATE_ASTRO_TRACKING:  # 15212
            try:v,_=_dvarint(data,1);self.state["tracking"]=bool(v)
            except:pass
        elif cmd==CMD_NOTIFY_STATE_CAPTURE_RAW_LIVE_STACKING:  # 15208
            try:v,_=_dvarint(data,1);self.state["stacking"]=bool(v)
            except:pass
        elif cmd==CMD_NOTIFY_PROGRASS_CAPTURE_RAW_LIVE_STACKING:  # 15209
            try:v,_=_dvarint(data,1);self.state["stacking_progress"]=v
            except:pass
        elif cmd==CMD_NOTIFY_FOCUS_POSITION:  # 15257
            try:v,_=_dvarint(data,1);self.state["focus_position"]=v
            except:pass
        if self.on_notify:self.on_notify(pkt)
    def _on_error(self,ws,e):
        log.error(f"WS error: {e}")
        self.state["connected"]=False
    def _on_close(self,ws,c,r):self._connected.clear();self.state["connected"]=False
    def send(self,cmd,data=b""):
        if not self._connected.is_set():return False
        self._ws.send(build_ws_packet(cmd,data,self.device_id,self.client_id),opcode=websocket.ABNF.OPCODE_BINARY)
        self.state["last_cmd"]=cmd;return True
    def enter_camera(self, encode_type=1):
        """
        CMD_GLOBAL_TASK_MANAGER_ENTER_CAMERA (16404).
        Sent by the app BEFORE open_camera to initialise the camera subsystem.
        Payload: ReqEnterCamera { client_param { encode_type: 1 } }
        encode_type 1 = H.265/HEVC (activates RTSP encoder).
        """
        # ReqEnterCamera.ClientParams: field 1 = encode_type (varint)
        client_params = _field(1, 0, encode_type)           # encode_type
        # ReqEnterCamera: field 1 = client_param (bytes/embedded message)
        data = _field(1, 2, client_params)
        self.send(CMD_GLOBAL_TASK_MANAGER_ENTER_CAMERA, data)

    def open_camera(self, binning=False, rtsp_encode_type=1):
        """
        CMD_CAMERA_TELE_OPEN_CAMERA (10000).
        Must be called AFTER enter_camera().
        Payload: ReqOpenCamera { binning: false, rtsp_encode_type: 1 }
        rtsp_encode_type 1 = H.265 — this is what activates the RTSP stream.
        Without this payload the RTSP server stays silent.
        """
        # ReqOpenCamera: field 1 = binning (varint bool), field 2 = rtsp_encode_type (varint)
        data = _field(1, 0, 1 if binning else 0) + _field(2, 0, rtsp_encode_type)
        self.send(CMD_CAMERA_TELE_OPEN_CAMERA, data)

    def open_camera_wide(self, binning=False, rtsp_encode_type=1):
        """CMD_CAMERA_WIDE_OPEN_CAMERA (12000) with same payload."""
        data = _field(1, 0, 1 if binning else 0) + _field(2, 0, rtsp_encode_type)
        self.send(CMD_CAMERA_WIDE_OPEN_CAMERA, data)
    def close_camera(self):self.send(CMD_CAMERA_TELE_CLOSE_CAMERA)
    def take_photo(self):self.send(CMD_CAMERA_TELE_PHOTOGRAPH)
    def take_photo_raw(self):self.send(CMD_CAMERA_TELE_PHOTO_RAW)
    def start_burst(self,n=3):self.send(CMD_CAMERA_TELE_BURST,p_int(n))
    def stop_burst(self):self.send(CMD_CAMERA_TELE_STOP_BURST)
    def start_record(self):self.send(CMD_CAMERA_TELE_START_RECORD)
    def stop_record(self):self.send(CMD_CAMERA_TELE_STOP_RECORD)
    def start_timelapse(self):self.send(CMD_CAMERA_TELE_START_TIMELAPSE_PHOTO)
    def stop_timelapse(self):self.send(CMD_CAMERA_TELE_STOP_TIMELAPSE_PHOTO)
    def set_exposure(self,i):self.send(CMD_CAMERA_TELE_SET_EXP,p_int(i))
    def set_gain(self,i):self.send(CMD_CAMERA_TELE_SET_GAIN,p_int(i))
    def set_brightness(self,v):self.send(CMD_CAMERA_TELE_SET_BRIGHTNESS,p_int(v))
    def set_contrast(self,v):self.send(CMD_CAMERA_TELE_SET_CONTRAST,p_int(v))
    def set_saturation(self,v):self.send(CMD_CAMERA_TELE_SET_SATURATION,p_int(v))
    def set_sharpness(self,v):self.send(CMD_CAMERA_TELE_SET_SHARPNESS,p_int(v))
    def set_wb_mode(self,m):self.send(CMD_CAMERA_TELE_SET_WB_MODE,p_int(m))
    def set_wb_ct(self,i):self.send(CMD_CAMERA_TELE_SET_WB_CT,p_int(i))
    def set_ircut(self,v):self.send(CMD_CAMERA_TELE_SET_IRCUT,p_int(v))
    def set_jpg_quality(self,q):self.send(CMD_CAMERA_TELE_SET_JPG_QUALITY,p_int(q))
    def switch_resolution(self,i):self.send(CMD_CAMERA_TELE_SWITCH_RESOLUTION,p_int(i))
    def switch_framerate(self,i):self.send(CMD_CAMERA_TELE_SWITCH_FRAMERATE,p_int(i))
    def get_all_params(self):self.send(CMD_CAMERA_TELE_GET_ALL_PARAMS)
    def start_calibration(self,lat=0.0,lon=0.0):
        d=_field(1,1,float(lon))+_field(2,1,float(lat))  # ReqStartCalibration: field1=lon, field2=lat
        self.send(CMD_ASTRO_START_CALIBRATION,d)
    def stop_calibration(self):self.send(CMD_ASTRO_STOP_CALIBRATION)
    def goto_dso(self,ra,dec,name=""):self.send(CMD_ASTRO_START_GOTO_DSO,p_goto_dso(ra,dec,name))
    def goto_solar(self,i):self.send(CMD_ASTRO_START_GOTO_SOLAR_SYSTEM,p_int(i))
    def stop_goto(self):self.send(CMD_ASTRO_STOP_GOTO)
    def one_click_goto_dso(self,ra,dec,name=""):self.send(CMD_ASTRO_START_ONE_CLICK_GOTO_DSO,p_goto_dso(ra,dec,name))
    def stop_one_click_goto(self):self.send(CMD_ASTRO_STOP_ONE_CLICK_GOTO)
    def go_live(self):self.send(CMD_ASTRO_GO_LIVE)
    def go_live_wide(self):self.send(CMD_ASTRO_WIDE_GO_LIVE)
    def start_stacking(self,exp_ms=10000,gain=0,count=0):
        d=b""
        if exp_ms:d+=_field(1,0,exp_ms)
        if gain:d+=_field(2,0,gain)
        if count:d+=_field(3,0,count)
        self.send(CMD_ASTRO_START_CAPTURE_RAW_LIVE_STACKING,d)
    def stop_stacking(self):self.send(CMD_ASTRO_STOP_CAPTURE_RAW_LIVE_STACKING)
    def start_plate_solve(self):self.send(CMD_ASTRO_START_EQ_SOLVING)
    def stop_plate_solve(self):self.send(CMD_ASTRO_STOP_EQ_SOLVING)
    def start_sky_finder(self):self.send(CMD_ASTRO_START_SKY_TARGET_FINDER)
    def stop_sky_finder(self):self.send(CMD_ASTRO_STOP_SKY_TARGET_FINDER)
    def start_ai_enhance(self):self.send(CMD_ASTRO_START_AI_ENHANCE)
    def stop_ai_enhance(self):self.send(CMD_ASTRO_STOP_AI_ENHANCE)
    def one_click_shoot(self):self.send(CMD_ASTRO_START_ONE_CLICK_SHOOTING)
    def auto_focus(self):self.send(CMD_FOCUS_AUTO_FOCUS)
    def focus_step(self,s=1):self.send(CMD_FOCUS_MANUAL_SINGLE_STEP,p_int(s))
    def focus_in(self):self.send(CMD_FOCUS_START_MANUAL_CONTINUOUS,p_int(-1))
    def focus_out(self):self.send(CMD_FOCUS_START_MANUAL_CONTINUOUS,p_int(1))
    def focus_stop(self):self.send(CMD_FOCUS_STOP_MANUAL_CONTINUOUS)
    def astro_focus(self):self.send(CMD_FOCUS_START_ASTRO_AUTO_FOCUS)
    def stop_astro_focus(self):self.send(CMD_FOCUS_STOP_ASTRO_AUTO_FOCUS)
    def joystick(self, x, y):
        """
        Move motors. x/y each in range -100..100.
        Positive x = East (right), positive y = North (up).
        Converts to polar (vectorAngle, vectorLength) as required by ReqMotorServiceJoystick.
        """
        angle, length = xy_to_polar(x, y)
        self.send(CMD_STEP_MOTOR_JOYSTICK, p_joystick(angle, length))
    def joystick_stop(self):self.send(CMD_STEP_MOTOR_JOYSTICK_STOP)  # ReqMotorServiceJoystickStop has no payload
    def start_tracking(self):self.send(CMD_TRACK_START_TRACK)
    def stop_tracking(self):self.send(CMD_TRACK_STOP_TRACK)
    def set_location(self,lat,lon,alt=0):self.send(CMD_SYSTEM_SET_LOCATION,p_location(lat,lon,alt))
    def sync_time(self):self.send(CMD_SYSTEM_SET_TIME,p_int(int(time.time()*1000)))
    def reboot(self):self.send(CMD_RGB_POWER_REBOOT)
    def power_down(self):self.send(CMD_RGB_POWER_POWER_DOWN)
    def led_on(self):self.send(CMD_RGB_POWER_POWERIND_ON)
    def led_off(self):self.send(CMD_RGB_POWER_POWERIND_OFF)
    def get_device_state(self):self.send(CMD_GLOBAL_TASK_GET_DEVICE_STATE_INFO)
    def http_device_info(self):
        try:
            r=requests.post(f"http://{self.host}:{self.HTTP_PORT}/deviceInfo",json={},timeout=5)
            return r.json()
        except Exception as e:return {"error":str(e)}

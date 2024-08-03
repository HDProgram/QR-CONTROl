import cv2, numpy as np, time, os, sys, keyboard as kb
from pyzbar.pyzbar import decode
from plutocontrol import pluto
from multiprocessing import Process, Queue, Value

def qr_code_detection(q):
    os.dup2(os.open(os.devnull, os.O_RDWR), sys.stderr.fileno())
    cap = cv2.VideoCapture(0)
    cap.set(3, 640), cap.set(4, 480)
    detected_qr_codes = {}
    while cap.isOpened():
        ret, img = cap.read()
        if not ret: break
        for barcode in decode(img):
            myData = barcode.data.decode('utf-8').lower()
            if myData not in detected_qr_codes or (time.time() - detected_qr_codes[myData] > 5):
                detected_qr_codes[myData] = time.time()
                q.put(myData)
            pts = np.array([barcode.polygon], np.int32).reshape((-1, 1, 2))
            cv2.polylines(img, [pts], True, (255, 0, 255), 5)
            cv2.putText(img, myData, barcode.rect[:2], cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 0, 255), 2)
        cv2.imshow('Result', img)
        if cv2.waitKey(1) & 0xFF == ord('q'): break
    cap.release(), cv2.destroyAllWindows()

def execute_qr_action(q, armed_status):
    my_pluto = pluto()
    qr_code_actions = {
        'arm': lambda: (my_pluto.arm(), setattr(armed_status, 'value', 1)),
        'disarm': lambda: (my_pluto.disarm(), setattr(armed_status, 'value', 0)),
        'land': my_pluto.land, 'takeoff': my_pluto.take_off,
    }
    while True:
        qr_code_actions.get(q.get().lower(), lambda: None)()

def keyboard_control(armed_status):
    my_pluto = pluto()
    my_pluto.cam()
    actions = {
        70: lambda: (my_pluto.disarm() if armed_status.value else my_pluto.arm(), setattr(armed_status, 'value', 0 if armed_status.value else 1)),
        10: my_pluto.forward, 30: my_pluto.left, 40: my_pluto.right, 80: my_pluto.reset, 50: my_pluto.increase_height,
        60: my_pluto.decrease_height, 110: my_pluto.backward, 130: my_pluto.take_off, 140: my_pluto.land,
        150: my_pluto.left_yaw, 160: my_pluto.right_yaw, 120: lambda: (print("Developer Mode ON"), setattr(my_pluto, 'rcAUX2', 1500)),
        200: my_pluto.connect, 210: my_pluto.disconnect
    }
    key_map, keyboard_cmds = {'up': '[A', 'down': '[B', 'left': '[D', 'right': '[C', 'space': ' '}, {
        '[A': 10, '[D': 30, '[C': 40, 'w': 50, 's': 60, ' ': 70, 'r': 80, '[B': 110, 'q': 130, 'e': 140,
        'a': 150, 'd': 160, 'n': 120, '1': 25, '2': 30, '3': 35, '4': 45, 'c': 200, 'x': 210
    }
    while True:
        if kb.is_pressed('e'): break
        key = kb.read_event()
        if key.event_type == kb.KEY_DOWN:
            actions.get(keyboard_cmds.get(key_map.get(key.name, key.name), 80), my_pluto.reset)()

if __name__ == '__main__':
    q, armed_status = Queue(), Value('i', 0)
    Process(target=qr_code_detection, args=(q,)).start()
    Process(target=execute_qr_action, args=(q, armed_status)).start()
    Process(target=keyboard_control, args=(armed_status,)).start()

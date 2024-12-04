import cv2
import numpy as np
from picamera2 import Picamera2
import time
import subprocess
from flask import Flask, render_template, Response, request, make_response
from functools import wraps
import threading
import serial

app = Flask(__name__)

USERNAME = 'admin'  
PASSWORD = 'password'  

def check_auth(username, password):
    return username == USERNAME and password == PASSWORD

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return make_response('Login required', 401, 
                                 {'WWW-Authenticate': 'Basic realm="Login Required"'})
        return f(*args, **kwargs)
    return decorated

picam2 = Picamera2()
picam2.configure(picam2.create_preview_configuration(main={"format": 'XRGB8888', "size": (640, 480)}))
picam2.start()

face_cascade = cv2.CascadeClassifier('/home/pi/opencv-4.x/data/haarcascades/haarcascade_frontalface_alt.xml')

last_face_time = time.time()
FACE_TIMEOUT = 10 
frame_global = None
ser = None
camera_active = False
buzzer_on = False  # 부저 상태 추적
message_sent = False

def generate_frames():
    while True:
        if frame_global is not None:
            ret, buffer = cv2.imencode('.jpg', frame_global)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        time.sleep(0.1)

@app.route('/')
@requires_auth  
def index():
    return render_template('index.html')

@app.route('/video_feed')
@requires_auth  
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

def run_flask():
    app.run(host='0.0.0.0', port=5000)

def main_loop():
    global frame_global, last_face_time, camera_active, ser, buzzer_on

    try:
        ser = serial.Serial('/dev/ttyUSB0', 9600, timeout=1)
        ser.flush()

        while True:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8').strip()
                if line == "ON" and not camera_active:
                    camera_active = True
                    print("Camera ON")
                    last_face_time = time.time()
                elif line == "OFF" and camera_active:
                    camera_active = False
                    print("Camera OFF")
                    frame_global = None
                    if buzzer_on:
                        ser.write(b"STOP_BUZZER\n")
                        buzzer_on = False

            if camera_active:
                frame = picam2.capture_array()
                frame_global = frame

                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = face_cascade.detectMultiScale(gray, 1.1, 3)

                if len(faces) > 0:
                    last_face_time = time.time()
                    message_sent = False
                    if buzzer_on:
                        print("Face detected, stopping buzzer...")
                        ser.write(b"STOP_BUZZER\n")
                        buzzer_on = False
                else:
                    if time.time() - last_face_time > FACE_TIMEOUT:
                        if not buzzer_on:
                            print("No face detected for 10 seconds, triggering buzzer...")
                        ser.write(b"START_BUZZER\n")
                        buzzer_on = True
                        if not message_sent:
                            try:
                                subprocess.run(['python3', '/home/pi/alarm_kakao/send_message.py'])
                                message_sent = True
                            except Exception as e:
                                print(f"error: {e}")

                for (x, y, w, h) in faces:
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)

                cv2.imshow('Baby Face Detection', frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

            time.sleep(0.1)

    finally:
        cv2.destroyAllWindows()
        picam2.stop()
        if ser:
            ser.close()

if __name__ == '__main__':
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    main_loop()

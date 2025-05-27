# 智慧夜燈系統（使用 Raspberry Pi + USB 繼電器 + IR Camera + USB LED）
# --- 使用套件 ---
# pyserial：控制 USB 繼電器
# opencv-python：讀取紅外線相機畫面
# mediapipe：分析人體姿勢
# datetime：判斷啟動時間區間

import cv2
import mediapipe as mp
import time
import serial
from datetime import datetime

# 設定設備路徑（用 ls /dev/serial/by-id/ 確認）
USB_LED_PORT = '/dev/serial/by-id/usb-relay-usbled'
IR_LED_PORT = '/dev/serial/by-id/usb-relay-irled'

# USB 繼電器初始化
usb_led = serial.Serial(USB_LED_PORT, 9600)
ir_led = serial.Serial(IR_LED_PORT, 9600)

def relay_on(relay):
    relay.write(b'\xA0\x01\x01\xA2')

def relay_off(relay):
    relay.write(b'\xA0\x01\x00\xA1')

def in_night_mode():
    now = datetime.now()
    return now.hour >= 0 and now.hour < 6

# MediaPipe 初始化
mp_pose = mp.solutions.pose
pose = mp_pose.Pose()

# 相機初始化（使用 Pi Camera 或 USB Camera）
cap = cv2.VideoCapture(0)

print("系統啟動中... 只在夜間模式才會偵測")

led_on_time = 0
LED_DURATION = 120  # 秒

while True:
    if not in_night_mode():
        time.sleep(60)
        continue

    # 確保 IR 補光燈長亮
    relay_on(ir_led)

    ret, frame = cap.read()
    if not ret:
        continue

    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = pose.process(rgb_frame)

    if results.pose_landmarks:
        landmarks = results.pose_landmarks.landmark
        nose_y = landmarks[mp_pose.PoseLandmark.NOSE].y
        hip_y = landmarks[mp_pose.PoseLandmark.LEFT_HIP].y

        # 假設 nose 高於 hip，代表起身（值越小代表越靠上）
        if nose_y < hip_y - 0.1:
            print("偵測到起身！啟動 USB LED")
            relay_on(usb_led)
            led_on_time = time.time()

    # 如果 LED 已經亮超過兩分鐘就關掉
    if led_on_time != 0 and time.time() - led_on_time > LED_DURATION:
        print("兩分鐘到，自動關閉 USB LED")
        relay_off(usb_led)
        led_on_time = 0

    time.sleep(1)  # 每秒判斷一次

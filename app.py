from flask import Flask, render_template, Response, request, jsonify
import cv2
import numpy as np
import time

net = cv2.dnn.readNetFromCaffe('resources\\MobileNetSSD_deploy.prototxt',
                               'resources\\MobileNetSSD_deploy.caffemodel')

app = Flask(__name__)

class VideoReader:
    def __init__(self, video_source='sample.mp4'):
        self.cap = cv2.VideoCapture(video_source)
        self.interline = -1
        self.line1X = 100
        self.line2X = 200
        self.startTime = 0
        self.endTime = 0
        self.distance = 2
        self.speed = 0
        self.CalcSpeed = 0
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.vehicle_detected = False
        self.save_image = False
        
        self.position = (30, 30)
        self.font_scale = 1.2
        self.font_color = (0, 0, 0)
        self.thickness = 2
        self.time = 0
        self.car_image_url = "static/cropped"

    def detect_MN(self, image):
        resized_image = cv2.resize(image, (300, 300))
        (startX, startY, endX, endY) = (0, 0, 0, 0)
        blob = cv2.dnn.blobFromImage(resized_image, 0.007843, (300, 300), 127.5)
        net.setInput(blob)
        detections = net.forward()
        if detections.shape[2] == 0:
            self.CalcSpeed = 0

            return image, startX, startY, endX, endY
        else:    
            for i in range(detections.shape[2]):
                confidence = detections[0, 0, i, 2]
                if confidence > 0.2:
                    class_id = int(detections[0, 0, i, 1])
                    if class_id == 7:
                        box = detections[0, 0, i, 3:7] * np.array([300, 300, 300, 300])
                        (startX, startY, endX, endY) = box.astype("int")
                        image = cv2.rectangle(resized_image, (startX, startY), (endX, endY), (255), 2)
                        if(self.save_image):
                            cropped = resized_image[startY:endY,startX:endX]
                            cv2.imwrite(self.car_image_url+f"{self.CalcSpeed:.2f}"+ ".jpg", cropped)
                            self.save_image = False
            return image, startX, startY, endX, endY

    def process_frame(self, frame, startX, startY, endX, endY):
        if (self.vehicle_detected == True):
            cv2.line(frame, (self.line1X, 50), (self.line1X, 250), (0, 255, 0), 2)
            cv2.line(frame, (self.line2X, 50), (self.line2X, 250), (0, 0, 255), 2)
            self.CalcSpeed = 0
       
        if not self.vehicle_detected:
            if self.line1X <= startX <= self.line2X:
                self.startTime = time.time()
                self.vehicle_detected = True
        else:
            if startX < self.line1X or startX > self.line2X:
                self.endTime = time.time()
                self.time = abs(self.endTime - self.startTime)
                if self.time != 0:
                    self.CalcSpeed =  3.6 * self.distance / self.time
                    self.save_image = True
                self.vehicle_detected = False


        ctext = f"{self.CalcSpeed:.2f} kmph"
        cv2.putText(frame, ctext, self.position, self.font, self.font_scale, self.font_color, self.thickness)

        return frame

    def get_frame(self):
        while True:
            ret, frame = self.cap.read()
            if not ret:
                print("Error reading frame")
                break

            frame, startX, startY, endX, endY = self.detect_MN(frame)
            frame = self.process_frame(frame, startX, startY, endX, endY)
            frame = cv2.resize(frame, (640, 480))

            _, jpeg = cv2.imencode('.jpg', frame)
            frame_bytes = jpeg.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n\r\n')

    def run(self):
        return Response(self.get_frame(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/')
def index():
    return render_template('speed.html')

@app.route('/speed', methods=['GET', 'POST'])
def speed():
    if request.method == 'POST':
        video_source = request.form.get('video_source', 0)
        pixel_per_meter = request.form.get('pixel_per_meter', 10)
        video_reader.cap.release()
        if video_source == "-1":
            video_reader.cap = cv2.VideoCapture("sample.mp4")
            print("Showing video")
        else:
            video_reader.cap = cv2.VideoCapture(int(video_source))
        video_reader.pixel_per_meter = int(pixel_per_meter)

    return render_template('speed.html')

@app.route('/video')
def video():
    return video_reader.run()

@app.route('/get_car_data')
def get_car_data():
    return jsonify({
        'car_image_url': video_reader.car_image_url,
        # 'car_speed': video_reader.CalcSpeed
        'car_speed': f"{video_reader.CalcSpeed:.2f}"
    })

if __name__ == "__main__":
    video_reader = VideoReader()
    app.run(debug=True)

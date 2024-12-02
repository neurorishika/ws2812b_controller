import socket
import struct
import time
import numpy as np
from rpi_ws281x import *

class LEDMatrix:
    """Class to control a WS2812B LED matrix display with serpentine pattern handling."""

    def __init__(self, rows, cols, pin=18, freq_hz=800000, dma=10, brightness=5, invert=False, channel=0):
        self.rows = rows
        self.cols = cols
        self.led_count = rows * cols
        self.strip = Adafruit_NeoPixel(self.led_count, pin, freq_hz, dma, invert, brightness, channel)
        self.strip.begin()

    def display_image(self, image_array):
        """Display an (rows, cols, 3) image array on the LED matrix with serpentine pattern handling."""
        self.clear_matrix()
        for row in range(self.rows):
            for col in range(self.cols):
                red, green, blue = image_array[row][col]
                led_index = row * self.cols + (col if row % 2 == 0 else self.cols - 1 - col)
                self.strip.setPixelColor(led_index, Color(int(np.clip(red,0,255)), int(np.clip(green,0,255)), int(np.clip(blue,0,255))))
        self.strip.show()
        print("Displayed new image on LED matrix with serpentine pattern.")

    def clear_matrix(self):
        """Turn off all LEDs on the matrix."""
        for i in range(self.led_count):
            self.strip.setPixelColor(i, Color(0, 0, 0))
        self.strip.show()
        print("Cleared LED matrix.")

    def test_pattern(self, color_sequence):
        """Run a simple test pattern across all LEDs based on a color sequence."""
        for color in color_sequence:
            for i in range(self.led_count):
                self.strip.setPixelColor(i, color)
            self.strip.show()
            time.sleep(0.5)
        print("Completed test pattern.")

    def rainbow_sweep(self, delay_ms=20):
        """Run a rainbow sweep pattern across the LED matrix."""
        for j in range(256):
            for i in range(self.led_count):
                row, col = divmod(i, self.cols)
                index = i if row % 2 == 0 else row * self.cols + (self.cols - 1 - col)
                color = self.wheel((i + j) & 255)
                self.strip.setPixelColor(index, color)
            self.strip.show()
            time.sleep(delay_ms / 1000.0)
        print("Completed rainbow sweep pattern.")

    def wheel(self, pos):
        """Generate rainbow colors across 0-255 positions."""
        if pos < 85:
            return Color(pos * 3, 255 - pos * 3, 0)
        elif pos < 170:
            pos -= 85
            return Color(255 - pos * 3, 0, pos * 3)
        else:
            pos -= 170
            return Color(0, pos * 3, 255 - pos * 3)


class LEDClient:
    """Client to receive and display images or run test patterns on LED matrix using binary protocol."""

    def __init__(self, host='0.0.0.0', port=65432):
        self.host = host
        self.port = port
        self.led_matrix = None

    def start(self):
        """Start the client and persistently listen for incoming data."""
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.bind((self.host, self.port))
        client_socket.listen(1)
        print(f"Client listening on {self.host}:{self.port}")

        while True:
            conn, addr = client_socket.accept()
            print(f"Connected by {addr}")

            try:
                while True:
                    # Read the 8-byte header
                    header = conn.recv(8)
                    if not header:
                        break
                    message_type, data_length = struct.unpack('!II', header)

                    if message_type == 0:  # Setup message for matrix size
                        rows, cols = data_length, struct.unpack('!I', conn.recv(4))[0]
                        print(f"Initializing LED matrix with size {rows}x{cols}")
                        self.led_matrix = LEDMatrix(rows, cols)  # Initialize matrix with new dimensions

                    elif message_type == 1:  # Image data
                        print("Receiving image data")
                        flat_image_data = conn.recv(data_length)
                        image_array = np.frombuffer(flat_image_data, dtype=np.uint8).reshape((self.led_matrix.rows, self.led_matrix.cols, 3))
                        self.led_matrix.display_image(image_array)

                    elif message_type == 2:  # Test pattern command
                        print(f"Received test pattern command: code {data_length}")
                        if data_length == 1:
                            self.run_test_pattern("rgb_sweep")
                        elif data_length == 2:
                            self.run_test_pattern("rainbow_sweep")
                        else:
                            print("Unknown test pattern code received.")

            except Exception as e:
                print(f"Connection error: {e}")
            finally:
                # Clear matrix on disconnect and continue listening for new connections
                if self.led_matrix:
                    self.led_matrix.clear_matrix()
                conn.close()
                print("Connection closed. Waiting for new connection.")

    def run_test_pattern(self, pattern_name):
        """Run a pre-defined test pattern based on the pattern name."""
        print(f"Running test pattern: {pattern_name}")
        if pattern_name == "rgb_sweep":
            self.led_matrix.test_pattern([Color(255, 0, 0), Color(0, 0, 255), Color(0, 255, 0)])
        elif pattern_name == "rainbow_sweep":
            self.led_matrix.rainbow_sweep()
        else:
            print(f"Error: Unknown test pattern '{pattern_name}'.")


if __name__ == "__main__":
    client = LEDClient()  
    client.start()

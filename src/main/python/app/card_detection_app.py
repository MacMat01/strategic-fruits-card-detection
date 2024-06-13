﻿import time

import cv2
from pyzbar.pyzbar import decode

from manager.card_manager import CardManager
from manager.influxdb_manager import InfluxDBManager
from manager.player_manager import PlayerManager
from manager.video_capture_manager import VideoCaptureManager
from manager.yolo_model_manager import YOLOModelManager


class CardDetectionApp:
    """
    The CardDetectionApp class manages the detection and processing of cards and players
    in a video stream. It uses various managers to handle the different aspects of the
    process, including video capture, YOLO model for object detection, and InfluxDB for
    data storage.

    Attributes:
        influxdb_manager (InfluxDBManager): Manages interactions with InfluxDB.
        video_capture_manager (VideoCaptureManager): Handles video capture.
        yolo_model_manager (YOLOModelManager): Manages YOLO model for object detection.
        player_manager (PlayerManager): Manages player-related data and actions.
        card_manager (CardManager): Manages card-related data and actions.
        first_phase_rounds (int): Number of rounds in the first phase.
        round_number (int): The current round number.
    """

    def __init__(self, video_file=None):
        """
        Initializes the CardDetectionApp with optional video file input.
        
        Args:
            video_file (str, optional): Path to the video file. If None, captures from camera.
        """
        self.influxdb_manager = InfluxDBManager()
        self.video_capture_manager = VideoCaptureManager(video_file)
        self.yolo_model_manager = YOLOModelManager()
        self.player_manager = PlayerManager()
        self.card_manager = CardManager()
        self.first_phase_rounds = 2
        self.round_number = 1
        print(f"Round {self.round_number} starting.")

    def increment_round(self):
        """
        Increments the round number and prints the new round number.
        """
        self.round_number += 1
        print(f"Round {self.round_number} starting.")

    def check_round_end(self):
        """
        Checks if the current round should end based on the number of detected cards,
        and ends the round if necessary.
        """
        if self.round_number <= self.first_phase_rounds and len(self.card_manager.cards) == 4:
            self.end_round()
        elif self.round_number > self.first_phase_rounds and len(self.card_manager.cards) == 8:
            self.end_round()

    def end_round(self):
        """
        Ends the current round, processes data, clears sets, and starts a new round after a delay.
        """
        print(f"Round {self.round_number} ended and starting 10 seconds delay")
        time.sleep(10)
        print(f"10 seconds delay ended and starting {self.round_number + 1} round.")
        matched_players_cards = self.write_to_influxdb()
        for player, player_time, card in matched_players_cards:
            if (player, player_time) in self.player_manager.players_first_set:
                self.player_manager.players_first_set.remove((player, player_time))
            else:
                self.player_manager.players_second_set.remove((player, player_time))
            if card in self.card_manager.cards:
                self.card_manager.cards.remove(card)
            elapsed_time = time.time() - player_time
            self.influxdb_manager.write_to_influxdb(player, card, elapsed_time)
        self.player_manager.players_first_set.clear()
        self.player_manager.players_second_set.clear()
        self.card_manager.cards.clear()
        self.increment_round()

    def process_card_detection(self, detected_cards):
        """
        Processes detected cards and checks if the round should end.
        
        Args:
            detected_cards (list): List of detected cards.
        """
        self.card_manager.detect_card_played(detected_cards)
        self.check_round_end()

    def detect_and_process_qrcodes(self, frame):
        """
        Detects and processes QR codes in a video frame.
        
        Args:
            frame (ndarray): The video frame to process.
        """
        detected_qrcodes = self.detect_players(frame)
        self.player_manager.process_qrcode(detected_qrcodes, self.round_number, self.card_manager.cards,
                                           self.first_phase_rounds)

    def detect_and_process_cards(self, frame):
        """
        Detects and processes cards in a video frame.
        
        Args:
            frame (ndarray): The video frame to process.
        """
        detect_result = self.yolo_model_manager.detect_objects(frame)
        detected_cards_indices = detect_result[0].boxes.cls.tolist()
        detected_cards = [detect_result[0].names[i] for i in detected_cards_indices]
        self.process_card_detection(detected_cards)

    def write_to_influxdb(self):
        """
        Matches players to cards and writes the matched data to InfluxDB.
        
        Returns:
            list: List of tuples containing matched player, player time, and card.
        """

        def match_players_cards(players):
            for player, player_time in players:
                for card in self.card_manager.cards:
                    if player[0].lower() == card[-1].lower() and (
                            player, player_time, card) not in matched_players_cards:
                        matched_players_cards.append((player, player_time, card))
                        print(f"Matched: Player '{player}' with Card '{card}'")
                        break

        matched_players_cards = []
        match_players_cards(self.player_manager.players_first_set)
        match_players_cards(self.player_manager.players_second_set)
        return matched_players_cards

    def process_frame(self):
        """
        Processes a single frame of the video stream.
        
        Returns:
            bool: True if frame processing was successful, False otherwise.
        """
        ret, frame = self.video_capture_manager.read_frame()
        if not ret:
            return False

        self.detect_and_process_qrcodes(frame)
        detect_result = self.yolo_model_manager.detect_objects(frame)
        detect_image = detect_result[0].plot()
        self.detect_and_process_cards(frame)

        cv2.imshow('Card Detection', detect_image)

        return True

    def run(self):
        """
        Runs the main loop for processing the video stream.
        """
        while True:
            if not self.process_frame() or cv2.waitKey(1) & 0xFF == ord('q'):
                break

        self.video_capture_manager.release()
        cv2.destroyAllWindows()

    @staticmethod
    def detect_players(frame):
        """
        Detects players by scanning QR codes in a video frame.
        
        Args:
            frame (ndarray): The video frame to scan.
        
        Returns:
            list: List of detected player identifiers.
        """
        qrcodes = decode(frame)
        detected_players = [qrcode.data.decode('utf-8') for qrcode in qrcodes]
        return detected_players


if __name__ == "__main__":
    app = CardDetectionApp()
    app.run()

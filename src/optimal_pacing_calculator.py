import numpy as np
import utils

class OptimalPacingCalculator:
    def __init__(self, race_course, target_time):
        """
        race_course: An object containing course information, such as grades and segment lengths.
        target_time: The total time goal for completing the course.
        """
        self.race_course = race_course
        self.target_time = target_time
        self.segment_lengths = self.race_course.segment_lengths
        self.grades = self.race_course.grades
        
        self.adjustments = utils.get_pace_adjustments(self.grades)
        self.base_pace = self.calculate_base_pace()
        self.optimal_paces = self.base_pace + self.adjustments

        # Calculate optimal segment times
        self.optimal_seg_times = np.multiply(self.segment_lengths, self.optimal_paces)

        # Create the weighted paces array
        self.weighted_paces = self.calculate_weighted_paces()

    def calculate_base_pace(self):
        """
        Calculates the base pace for the race course.
        """
        total_adjusted_time = np.dot(self.adjustments, self.segment_lengths)
        total_distance = np.sum(self.segment_lengths)
        return (self.target_time - total_adjusted_time) / total_distance

    def calculate_weighted_paces(self):
        """
        Creates a nested dictionary where:
        weighted_paces[i][j] = the weighted optimal pace for the segment from i to j.
        """
        n = len(self.segment_lengths)
        weighted_paces = {}

        for i in range(n):
            weighted_paces[i] = {}
            for j in range(i + 1, n + 1):
                segment_lengths = self.segment_lengths[i:j]
                segment_paces = self.optimal_paces[i:j]
                total_length = np.sum(segment_lengths)

                if total_length > 0:
                    # Weighted average pace for the segment [i:j]
                    weighted_paces[i][j] = np.dot(segment_paces, segment_lengths / total_length).round(4)

        return weighted_paces
        
    def get_weighted_paces(self):
        return self.weighted_paces

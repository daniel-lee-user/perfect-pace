import numpy as np
import math
import random
from abc import ABC, abstractmethod
import race_course
import utils
import matplotlib.pyplot as plt
from matplotlib import cm
import matplotlib.colors as mcolors

class SegmentingPlan(ABC):
    BRIGHT_COLORS = [
                '#FF0000', # Red (Bright)
                '#FFFF00', # Yellow
                '#00FF00', # Green
                '#00FFFF', # Cyan
                '#FF00FF', # Magenta
                '#FFA500', # Orange
                '#0000FF', # Blue
                '#800080', # Purple
                '#008000', # Dark Green (Dark)
            ]

    def __init__(self, race_course):
        self.race_course = race_course
        self.segment_indices = []  # List of starting indices for segments
        self.segment_distances = []  # Distances for each segment
        self.total_distance = self.race_course.total_distance

    @abstractmethod
    def _calculate_segments(self):
        """
        Abstract method to define how to segment the course.
        Derived classes will implement this method.
        """
        pass

    def calculate_segments(self):
        """
        Compute segment segments and store in segment_indices.
        """
        self.segment_indices = self._calculate_segments() + [self.race_course.n_segments]

        self.segment_distances = []
        for i in range(len(self.segment_indices) - 1):
            start = self.segment_indices[i]
            end = self.segment_indices[i + 1]
            segment_length = np.sum(self.race_course.segment_lengths[start:end])
            self.segment_distances.append(segment_length)

        return self.segment_indices

    def get_segments(self):
        return self.segment_indices

    def plot_segments(self, file_path=None, title=None):
        """
        Plot the segments on an elevation graph of the race course.
        """
        colors = SegmentingPlan.BRIGHT_COLORS[:]
        random.shuffle(colors)

        x = np.insert(self.race_course.end_distances, 0, 0)
        y = self.race_course.elevations

        plt.figure(figsize=(15, 8))
        plt.plot(x, y, color='gray', linewidth=0.5, label="Elevation Profile (Outline)")  # Plot full elevation curve

        # Highlight the area under the elevation curve for each segment
        for i in range(len(self.segment_indices) - 1):
            start_idx = self.segment_indices[i]
            end_idx = self.segment_indices[i + 1]

            segment_x = x[start_idx:end_idx + 1]
            segment_y = y[start_idx:end_idx + 1]

            color = colors[i % len(colors)]  # Cycle through the colors
            plt.fill_between(segment_x, segment_y, color=color, label=f"Segment {i + 1}", alpha=0.6)

        # Final segment if course not perfectly segmented
        if self.segment_indices[-1] < len(x) - 1:
            start_idx = self.segment_indices[-1]
            segment_x = x[start_idx:]
            segment_y = y[start_idx:]
            color = colors[len(self.segment_indices) % len(colors)]  # Cycle through the colors
            plt.fill_between(segment_x, segment_y, color=color, label=f"Segment {len(self.segment_indices)}", alpha=0.6)

        y_min, y_max = min(y), max(y)
        plt.ylim(y_min - 50, y_max + 50)

        plt.xlabel("Distance (miles)")
        plt.ylabel("Elevation (feet)")
        if title:
            plt.title(title)
        plt.legend(loc='upper right', fontsize='small')
        plt.grid(alpha=0.5)

        if file_path:
            plt.savefig(file_path, dpi=300, bbox_inches='tight')
            plt.close()
        else:
            plt.show()

class AveragePacePlan(SegmentingPlan):
    def __init__(self, race_course):
        super().__init__(race_course)

    def _calculate_segments(self):
        return [0]

class AveragePacePerMilePlan(SegmentingPlan):
    def __init__(self, race_course):
        super().__init__(race_course)

    def _calculate_segments(self):
        segments = [0]
        for i in range(1, math.ceil(self.race_course.total_distance)):
            mile_marker = np.argmin(
                np.abs(self.race_course.end_distances - i)
            )  # Find closest index to mile marker
            segments.append(int(mile_marker)) # Ensure mile_markers are ints (not np.int64)
        return segments

class AveragePacePerKilometerPlan(SegmentingPlan):
    def __init__(self, race_course):
        super().__init__(race_course)

    def _calculate_segments(self):
        segments = [0]
        end_distances_km = self.race_course.end_distances * utils.Conversions.MILES_TO_KM.value
        total_distance_km = self.race_course.total_distance * utils.Conversions.MILES_TO_KM.value
        for i in range(1, math.ceil(total_distance_km)):
            km_marker = np.argmin(
                np.abs(end_distances_km - i)
            )  # Find closest index to mile marker
            segments.append(int(km_marker)) # Ensure mile_markers are ints (not np.int64)
        return segments

class HillDetectionPlan(SegmentingPlan):
    MIN_HILL_DISTANCE = 350*utils.Conversions.METERS_TO_MILES.value # 350 Meters in Miles
    MIN_HILL_HEIGHT = 30    # Feet
    MIN_UPHILL_GRADE = 2    # Grade (smoothed)
    MIN_DOWNHILL_GRADE = 3  # Grade (smoothed)
    MIN_SEGMENT_LENGTH = .25    # Miles
    
    def __init__(self, race_course):
        super().__init__(race_course)
        
    def _calculate_segments(self):
        self.race_course.smoothen_segments(smoothen="gaussian") # Window should be 3
        grades = self.race_course.grades
        start_distances = self.race_course.start_distances
        end_distances = self.race_course.end_distances
        elevations = self.race_course.elevations
        distances = self.race_course.segment_lengths
        
        uphills, downhills = HillDetectionPlan.detect_hills(grades, start_distances, end_distances, elevations, 
            HillDetectionPlan.MIN_UPHILL_GRADE, HillDetectionPlan.MIN_DOWNHILL_GRADE, HillDetectionPlan.MIN_HILL_DISTANCE, HillDetectionPlan.MIN_HILL_HEIGHT)

        segments = HillDetectionPlan.get_spanning_segments(distances, elevations*utils.Conversions.FEET_TO_MILES.value, uphills, downhills, HillDetectionPlan.MIN_SEGMENT_LENGTH)
        return [start for start, _ in segments]

    @staticmethod
    def detect_hills(grades, start_distances, end_distances, elevations, uphill_cutoff, downhill_cutoff, min_length, min_height):    
        significant_uphills = (grades >= uphill_cutoff)
        significant_downhills = (grades <= -downhill_cutoff)

        uphill_segments = HillDetectionPlan.find_continuous_segments(significant_uphills, grades)
        downhill_segments = HillDetectionPlan.find_continuous_segments(significant_downhills, -grades)
        
        filtered_uphill_segments = HillDetectionPlan.filter_short_segments(uphill_segments, min_length, start_distances, end_distances)
        filtered_downhill_segments = HillDetectionPlan.filter_short_segments(downhill_segments, min_length, start_distances, end_distances)
        
        filtered_uphill_segments = HillDetectionPlan.filter_short_hills(filtered_uphill_segments, min_height, elevations)
        filtered_downhill_segments = HillDetectionPlan.filter_short_hills(filtered_downhill_segments, min_height, elevations)

        return filtered_uphill_segments, filtered_downhill_segments
    
    @staticmethod
    def filter_short_segments(segments, min_length, start_distances, end_distances):
        return [(start, end) for start, end in segments if end_distances[end] - start_distances[start] >= min_length]

    @staticmethod
    def filter_short_hills(segments, min_height, elevations):
        result = [(start, end) for start, end in segments if max(elevations[start:end+1]) - min(elevations[start:end+1]) >= min_height]
        return result
    
    @staticmethod
    def find_continuous_segments(hills, grades):
        segments = []
        start = None
        n = len(hills)
        i = 0
        
        while i < n:
            is_significant = hills[i]
            if is_significant:
                if start is None:
                    start = i
                i += 1
            else:
                i += 1
                if start is not None:
                    adjusted_start = HillDetectionPlan.adjust_point(start, grades, -1)
                    adjusted_end = HillDetectionPlan.adjust_point(i - 2, grades, 1)
                    segments.append((adjusted_start, adjusted_end))
                    start = None
                    i = adjusted_end + 1
                    
        if start is not None:
            adjusted_start = HillDetectionPlan.adjust_point(start, grades, -1)
            adjusted_end = n - 1
            segments.append((adjusted_start, adjusted_end))

        return segments

    @staticmethod
    def adjust_point(index, grades, coeff=1):
        n = len(grades)
        while index > 0 and index < n-1 and grades[index + coeff] >= 0:
            index += coeff
        return index

    @staticmethod
    def get_spanning_segments(distances, elevations, uphill_segments, downhill_segments, min_segment_length):
        all_segments = sorted(uphill_segments + downhill_segments, key=lambda x: x[0])
        full_course_segments = []
        filler_segments = []
        total_segments = len(distances)
        
        current_start = 0
        for (start, end) in all_segments:
            if current_start < start:
                full_course_segments.append((current_start, start - 1))
                filler_segments.append((current_start, start - 1))
            full_course_segments.append((start, end))        
            current_start = end + 1
        if current_start < total_segments:
            full_course_segments.append((current_start, total_segments - 1))
            filler_segments.append((current_start, total_segments - 1))

        return HillDetectionPlan.merge_filler_segments(distances, elevations, filler_segments, full_course_segments, min_segment_length)

    @staticmethod
    def merge_filler_segments(distances, elevations, filler_segments, full_course_segments, min_segment_length):
        merged_segments = []
        remove_next_segment = False
        for i, (start, end) in enumerate(full_course_segments):
            if (start, end) in filler_segments:
                segment_distance = sum(distances[start:end+1])
                if segment_distance < min_segment_length:
                    prev_segment = full_course_segments[i-1] if i > 0 else None
                    next_segment = full_course_segments[i+1] if i < len(full_course_segments) - 1 else None

                    segment_grade = utils.calculate_segment_grade(start, end, elevations, distances)
                    prev_grade = utils.calculate_segment_grade(prev_segment[0], prev_segment[1], elevations, distances) if prev_segment else None
                    next_grade = utils.calculate_segment_grade(next_segment[0], next_segment[1], elevations, distances) if next_segment else None

                    prev_grade_distance = abs(prev_grade - segment_grade) if prev_segment else None
                    next_grade_distance = abs(next_grade - segment_grade) if next_segment else None
                    
                    # Merge with the more similar adjacent segment
                    if prev_segment and (prev_grade_distance <= next_grade_distance or not next_segment):
                        merged_segments[-1] = (prev_segment[0], end)
                    elif next_segment:
                        merged_segments.append((start, next_segment[1])) # Assume next segment is not in filler
                        remove_next_segment = True
                    else:
                        merged_segments.append((start, end))
                else:
                    merged_segments.append((start, end))
            else:
                if remove_next_segment:
                    remove_next_segment = False
                else:
                    merged_segments.append((start, end))
        return merged_segments

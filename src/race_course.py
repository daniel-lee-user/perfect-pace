import gpxpy
import gpx_parser
import numpy as np
import matplotlib.pyplot as plt
import math
from gpx_parser import Segment
from scipy import ndimage
from utils import Conversions, Unit, SegmentType
import segments

import os

# TODO: Remove hard-coded conversions to feet and miles
# elevation data is stored as feet
# distance is stored as miles
# pace is stored as min/mile
class RaceCourse:
    def __init__(self, name):
        self.course_name = name
        self.segments: list[Segment] = None  # list of Segment objects

    @staticmethod
    def calculate_grade_scalar(elevation_change, distance):
        return (elevation_change / distance) * 100
    
    # TODO find some better arg values for smoothening function...
    def smoothen_segments(self, smoothen: str = "running_avg", *args):
        '''
        Smoothens the segments in this racecourse. NOTE: Only {running_avg} modifies segment data!
        Others directly modify self.grades and self.elevation_changes

        running_avg:    Box filter
        loess:          LOESS regression
        gaussian        1 4 6 4 1 filter

        :param str type: How to smoothen the course.
        '''
        if smoothen == "running_avg":
            WINDOW_SIZE = 3
            elevation = 0
            grade = 0
            slope_angle = 0
            dist = 0

            if len(self.segments) < WINDOW_SIZE:
                return

            # create an average window
            for i in range(WINDOW_SIZE):
                weight = self.segments[i].distance
                elevation += self.segments[i].elevation_change * weight
                grade += self.segments[i].grade * weight
                slope_angle += self.segments[i].slope_angle * weight
                dist += weight
            
            # iterate window through segments, skipping edges of filter
            for i in range(WINDOW_SIZE // 2, len(self.segments) - WINDOW_SIZE // 2):
                # update condition for the window, skip first instance since already computed
                if i != WINDOW_SIZE // 2:
                    # add new value
                    weight = self.segments[i + WINDOW_SIZE // 2].distance
                    elevation += self.segments[i + WINDOW_SIZE // 2].elevation_change * weight
                    grade += self.segments[i + WINDOW_SIZE // 2].grade * weight
                    slope_angle += self.segments[i + WINDOW_SIZE // 2].slope_angle * weight
                    dist += weight

                    # remove old value
                    weight = self.segments[i - WINDOW_SIZE // 2].distance
                    elevation -= self.segments[i - WINDOW_SIZE // 2].elevation_change * weight
                    grade -= self.segments[i - WINDOW_SIZE // 2].grade * weight
                    slope_angle -= self.segments[i - WINDOW_SIZE // 2].slope_angle * weight
                    dist -= weight

                self.segments[i].elevation_change = elevation / dist
                self.segments[i].grade = grade / dist
                self.segments[i].slope_angle = slope_angle / dist

                self.grades = np.array([self.segments[i].grade for i in range(len(self.segments))])
                self.elevation_changes = np.array([self.segments[i].elevation_change for i in range(len(self.segments))])

        elif smoothen == "loess":
            raise RuntimeError(f"Unimplemented smoothening argument: {smoothen}")
        elif smoothen == "gaussian":
            gaus_sigma = 5    # TODO find a better value?
            self.grades = np.array(ndimage.gaussian_filter1d(self.grades, gaus_sigma))
        else:
            raise RuntimeError(f"Unrecognized smmothening argument: {smoothen}!")

    def gen_course_plot(self, file_path):
        fig,ax = plt.subplots()
        fig.set_figwidth(20)
        
        distances = np.insert(self.end_distances, 0,0)
        full_elevations = np.append(self.start_elevations, self.end_elevations[-1])
        
        ax.plot(distances, full_elevations, label ='elevation', color='blue')
        ax.set_xlabel('distance (miles)')
        ax.set_ylabel('elevation (feet)')
        
        ax2 = ax.twinx()
        ax2.set_ylabel('grade (%)')
        full_grades = np.append(self.grades, self.grades[-1])
        ax2.step(distances, full_grades, label='grade', color='purple', where='post', alpha=0.4)
        
        fig.legend(loc="upper left", bbox_to_anchor=(0.125, 0.875))
        ax.set_title(self.course_name)
        plt.savefig(file_path, bbox_inches='tight',dpi=300)

    # TODO: hard coded smoothing values 
    # TODO: use more sophisticated smoothing method
    def smooth_attribute(self, attribute, param=10):
        smoothing_factor = max(int(self.n_segments/param), 1)
        smoothing_factor -= smoothing_factor % 2 == 0
        pad_width = int(smoothing_factor / 2)
        padded_attribute = np.pad(attribute, pad_width, 'edge')
        result = np.convolve(padded_attribute, np.ones(smoothing_factor), 'valid') / smoothing_factor
        return result
    
    def __repr__(self):
        unit_txt = 'miles' if self.units == Unit.IMPERIAL else 'meters'
        return(f"Course Name: {self.course_name} \n"\
               f"Total Distance: {self.total_distance:.2f} {unit_txt}\n"\
                f"Total Segments: {self.n_segments}")

class RealRaceCourse(RaceCourse):

    def __init__(self, name, file_path, N_SEGMENTS=300):
        super().__init__(name)

        self.segments = gpx_parser.parse_gpx(file_path) # remove after all references to segments are removed
        self.file_path = file_path

        self.calculate_distance = np.vectorize(RealRaceCourse.calculate_distance_scalar)
        self.calculate_grade_scalar = np.vectorize(RealRaceCourse.calculate_grade_scalar)
        
        lats, lons, raw_elevations = self.parse_gpx()
        lats = np.array(lats)
        lons = np.array(lons)
        raw_seg_lengths = self.calculate_distance(lats[:-1], lons[:-1], lats[1:], lons[1:])
        raw_elevations = np.array(raw_elevations)
        
        if np.isnan(raw_elevations).any():
            raise ValueError("nan values found in elevations")
        valid_indices = raw_seg_lengths != 0 # TODO: remove after interpolation pipeline is complete
        valid_indices_appended = np.append(valid_indices, True)
        segment_lengths = raw_seg_lengths[valid_indices]

        lats = lats[valid_indices_appended]
        lons = lons[valid_indices_appended]
        elevations = raw_elevations[valid_indices_appended]

        metric_view = segments.SegmentViewMetric(SegmentType.VARIABLE, lats, lons, segment_lengths, elevations)
        interpolated_unif = segments.SegmentViewInterpUniform(metric_view, N_SEGMENTS)
        smoothed_gaussian = segments.SegmentViewSmoothedGaussian(interpolated_unif, sigma =1)
        final_imperial = segments.SegmentViewImperial(smoothed_gaussian)
        self.change_view(final_imperial)
    
    def change_view(self, view: segments.SegmentView):
        self.n_segments = view.n_segments
        self.units = view.units
        self.lats = view.lats
        self.lons = view.lons
        self.distances = view.segment_lengths 
        self.start_distances = view.start_distances
        self.end_distances = view.end_distances
        self.total_distance = view.total_distance
        self.elevations = view.elevations
        self.start_elevations = view.start_elevations
        self.end_elevations = view.end_elevations
        self.elevation_changes = view.elevation_changes
        self.grades = view.grades
        self.current_view = view

    def parse_gpx(self):
        lats = []
        lons = []
        elevations = []

        with open(self.file_path, 'r') as gpx_file:
            gpx = gpxpy.parse(gpx_file)
            for track in gpx.tracks:
                for segment in track.segments:
                    for i in range(len(segment.points)):
                        point = segment.points[i]
                        if point.latitude is None or point.longitude is None or point.elevation is None:
                            raise ValueError(f"some of the trackpoint info is missing: {point}")
                        
                        lats.append(point.latitude)
                        lons.append(point.longitude)
                        elevations.append(point.elevation)

        return lats, lons, elevations

    @staticmethod
    def calculate_grade_scalar(elevation_change, distance):
        return elevation_change / distance * 100

    @staticmethod
    def calculate_distance_scalar(start_lat, start_lon, end_lat, end_lon):
        radius = 6371
        lat1, lon1, lat2, lon2 = map(math.radians, [start_lat, start_lon, end_lat, end_lon])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        distance = radius * c * 1000
        return distance

    def convert_metric_to_imperial(self):
        if self.units == Unit.IMPERIAL:
            return
        self.distances = self.distances * Conversions.METERS_TO_MILES.value 
        self.end_distances = self.end_distances * Conversions.METERS_TO_MILES.value
        self.start_distances =   self.start_distances * Conversions.METERS_TO_MILES.value
        self.total_distance = self.total_distance * Conversions.METERS_TO_MILES.value

        self.start_elevations = self.start_elevations * Conversions.METERS_TO_FEET.value
        self.end_elevations = self.end_elevations * Conversions.METERS_TO_FEET.value
        self.elevation_changes = self.elevation_changes * Conversions.METERS_TO_FEET.value
        
        self.units = Unit.IMPERIAL

class RandomRaceCourse(RaceCourse):
    def apply_smoothing(self):
        self.elevation_changes = self.smooth_attribute(self.elevation_changes, param=10)

    def __init__(self, name, n_segments, total_dist, use_smoothing=True):
        super().__init__(name)
        self.n_segments = n_segments

        avg_segment_dist = total_dist / n_segments
        margin = avg_segment_dist * 0.5
        seg_low = avg_segment_dist - margin
        seg_high = avg_segment_dist + margin

        self.distances = np.random.uniform(low=seg_low, high=seg_high, size=n_segments) # miles
                
        # TODO: improve hardcoded 100 value
        ELEVATION_SCALE = 100 * avg_segment_dist

        self.elevation_changes = np.random.normal(loc=0, scale=ELEVATION_SCALE, size=n_segments) 

        if use_smoothing:
            self.apply_smoothing()

        self.distances = self.distances * total_dist / (sum(self.distances))
        grade_vf = np.vectorize(self.calculate_grade_scalar)
        self.grades = grade_vf(self.elevation_changes * Conversions.FEET_TO_MILES.value ,self.distances) 
        self.total_distance = total_dist
        self.end_distances = np.cumsum(self.distances)
        self.start_distances = np.roll(self.end_distances,1)
        self.start_distances[0] = 0
        self.gen_elevations()

    def gen_elevations(self):
        
        self.end_elevations = np.cumsum(self.elevation_changes)
        self.start_elevations = np.roll(self.end_elevations,1)
        self.start_elevations[0] = 0

        min_val = min(self.end_elevations)

        self.start_elevations -= min_val
        self.end_elevations -= min_val
    
def main():
    for course_name in ['FH-Fox', 'boston']:# 'wineglass', 'lakefront', 'staten-half-elev']:
        file_path = f'data/{course_name}.gpx'
        course_name = os.path.basename(file_path).split('.')[0]
        for N_SEGMENTS in [125, 250, 500, 1000]:
            course = RealRaceCourse(course_name, file_path, N_SEGMENTS)
            directory = f'results/{course_name}/linear'
            if not os.path.exists(directory):
                os.makedirs(directory)
            course.gen_course_plot(f'{directory}/{N_SEGMENTS}.png')
            print(course)

if __name__ == '__main__':
    main()

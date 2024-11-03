import gpx_parser
import numpy as np
import matplotlib
from gpx_parser import Segment
from utils import cprint

conversion = {
    'meters_to_miles': 0.0006213712,
    'meters_to_feet': 3.28084,
    'miles_to_feet': 5280,
    'miles_to_meters': 1609.34,
    'feet_to_miles': 0.000189394,
    'feet_to_meters': 0.3048,
    'meters_to_km': 1000,
    'km_to_meters': 0.001
}

# TODO: Remove hard-coded conversions to feet and miles
# elevation data is stored as feet
# distance is stored as miles
# pace is stored as min/mile

class RaceCourse:
    def __init__(self, name):
        self.course_name = name
        self.segments: list[Segment] = None  # list of Segment objects

    @staticmethod
    def calculate_grade(elevation_change, distance):
        return (elevation_change / distance) * 100
    
    # TODO find some better arg values for smoothening function...
    def smoothen_segments(self, smoothen: str = "running avg", *args):
        '''
        Smoothens the segments in this racecourse. 

        NOTE: `running avg` modifies the actual segment values themselves and recomputes everything 
        (ie. if you initialized a new RaceCourse with those segment values), whereas `loess` only 
        modifies the arrays `elevation_change` and `grades`, leaving the original segment values unchanged.

        :param str type: How to smoothen the course.
        '''
        if smoothen == "running avg":
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
            
            # TODO implement edges too
            # iterate window through segments, skipping edges
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


                # self.segments[i].elevation_change = 0
                # self.segments[i].grade = 0
                # self.segments[i].slope_angle = 0

                self.segments[i].elevation_change = elevation / dist
                self.segments[i].grade = grade / dist
                self.segments[i].slope_angle = slope_angle / dist

                # TODO clean this up later, this is just a copy of a section of __init__
                self.elevation_changes = []
                self.elevations = []
                self.end_elevations = []
                self.grades = []
                self.distances = []

                for i in range(self.n_segments):
                    seg = self.segments[i]
                    try:
                        self.elevation_changes.append(seg.elevation_change * conversion['meters_to_miles']) 
                        self.elevations.append(seg.start_ele)
                        self.end_elevations.append(seg.end_ele)
                        self.grades.append(seg.grade)
                        self.distances.append(seg.distance * conversion['meters_to_miles']) 
                    except Exception as e:
                        print(f'error at segment {i}')   
                        print(repr(e))          

                self.end_distance = np.cumsum(self.distances)
                self.start_distance = np.roll(self.end_distance,1)
                self.start_distance[0] = 0
                self.total_distance = self.end_distance[-1]
                self.elevation_changes = np.array(self.elevation_changes)
                self.elevations = np.array(self.elevations)
                self.end_elevations = np.array(self.end_elevations)
                self.grades = np.array(self.grades)
                self.distances = np.array(self.distances)
        elif smoothen == "loess":
            raise RuntimeError(f"Unimplemented smoothening argument: {smoothen}")
        else:
            raise RuntimeError(f"Unrecognized smmothening argument: {smoothen}!")

        


    
    def gen_course_plot(self, file_path):
        fig,ax = matplotlib.pyplot.subplots()
        fig.set_figwidth(20)
        distances = np.insert(self.end_distance, 0,0)
        full_elevations = np.append(self.elevations, self.end_elevations[-1])
        ax.plot(distances, full_elevations, label ='elevation', color='blue')
        ax.set_xlabel('distance (miles)')
        ax.set_ylabel('elevation (feet)')
        ax2 = ax.twinx()
        ax2.set_ylabel('grade (%)')
        full_grades = np.append(self.grades, self.grades[-1])
        ax2.plot(distances, full_grades, label='grade', color='red')
        ax.set_title(self.course_name)
        matplotlib.pyplot.savefig(file_path, bbox_inches='tight',dpi=300)

    def repr_segment(self, i):
        raise NotImplementedError("You should implement this method on a subclass")

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
        return(f"Course Name: {self.course_name} \n"\
               f"Total Distance: {self.total_distance:.2f} miles\n"\
                f"Total Segments: {self.n_segments}")

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
        grade_vf = np.vectorize(self.calculate_grade)
        self.grades = grade_vf(self.elevation_changes *conversion['feet_to_miles'],self.distances) 
        self.total_distance = total_dist
        self.end_distance = np.cumsum(self.distances)
        self.start_distance = np.roll(self.end_distance,1)
        self.start_distance[0] = 0
        self.gen_elevations()

    def gen_elevations(self):
        
        self.end_elevations = np.cumsum(self.elevation_changes)
        self.elevations = np.roll(self.end_elevations,1)
        self.elevations[0] = 0

        min_val = min(self.end_elevations)

        self.elevations -= min_val
        self.end_elevations -= min_val
    
    def repr_segment(self,i):
        return (f"segment {i} \n"\
                f"{self.end_distance[i]:.2f} miles \n"\
                f"elevation: {self.elevations[i]:.2f} feet \n"\
                f"grade: {self.grades[i]:.2f} degrees")
        
class RealRaceCourse(RaceCourse):
    # TODO: IMPLEMENT OPTIMAL / ACCURATE ALGORITHM. 
    # VERIFY THAT THESE RECOMPUTED VALUES ARE STILL CLOSE TO THE ORIGINAL
    def apply_smoothing(self, param):
        # 1. smooth elevation
        self.elevations = self.smooth_attribute(self.elevations, param)
        self.end_elevations = self.smooth_attribute(self.end_elevations, param)
        # 2. recompute elevation changes
        self.elevation_changes = self.end_elevations - self.elevations
        # 3. recompute grades
        grade_vf = np.vectorize(self.calculate_grade)
        self.grades = grade_vf(self.elevation_changes *conversion['feet_to_miles'],self.distances) 

    def __init__(self, name, file_path, use_smoothing=False, param=10):
        super().__init__(name)
        self.segments = gpx_parser.parse_gpx(file_path)
        self.n_segments = len(self.segments)
        self.elevation_changes = []
        self.elevations = []
        self.end_elevations = []
        self.grades = []
        self.distances = []

        for i in range(self.n_segments):
            seg = self.segments[i]
            try:
                self.elevation_changes.append(seg.elevation_change * conversion['meters_to_miles']) 
                self.elevations.append(seg.start_ele)
                self.end_elevations.append(seg.end_ele)
                self.grades.append(seg.grade)
                self.distances.append(seg.distance * conversion['meters_to_miles']) 
            except Exception as e:
                print(f'error at segment {i}')   
                print(repr(e))          

        self.end_distance = np.cumsum(self.distances)
        self.start_distance = np.roll(self.end_distance,1)
        self.start_distance[0] = 0
        self.total_distance = self.end_distance[-1]
        self.elevation_changes = np.array(self.elevation_changes)
        self.elevations = np.array(self.elevations)
        self.end_elevations = np.array(self.end_elevations)
        self.grades = np.array(self.grades)
        self.distances = np.array(self.distances)

        if use_smoothing:
            self.apply_smoothing(param)

    def repr_segment(self,i):
        return (f"segment {i} \n"\
                f"@ ({self.segments[i].start_lat:.2f}, {self.segments[i].start_lon:.2f})\n"
                f"{self.end_distance[i]:.2f} miles \n"\
                f"elevation: {self.elevations[i]:.2f} feet \n"\
                f"grade: {self.grades[i]:.2f} degrees")
import numpy as np
import matplotlib.pyplot as plt
import race_course
from abc import ABC, abstractmethod
import json
import utils
import math
from enum import Enum

from numpy.typing import NDArray

# GENERAL NOTE: for now, all units below are in feet for elevation and miles for distance (for readability). 
# later, we want to be able to work in any metric or imperial units.

class ExportMode(Enum):
    FULL = 1
    ABBREV = 2
    PER_MILE = 3

class PacingPlan(ABC):
    def __init__(self, race_course, target_time, total_paces):
        self.target_time = target_time
        self.race_course = race_course
        self.total_paces = total_paces
        grades = self.race_course.grades
        adjustments = utils.get_pace_adjustments(grades)
        self.base_pace = (self.target_time - np.dot(adjustments, self.get_segment_lengths())) / np.sum(self.get_segment_lengths())
        self.optimal_paces = np.full(grades.shape, self.base_pace) + adjustments
        self.optimal_seg_times = np.multiply(self.get_segment_lengths(), self.optimal_paces)

        n = self.get_n_segments()
        self.weighted_paces = np.zeros((n,n+1))
        for i in range(n):
                for j in range(i+1, n+1):
                    self.weighted_paces[i,j] = np.dot(self.optimal_paces[i:j], self.get_segment_lengths()[i:j] / sum(self.get_segment_lengths()[i:j]))
    
    def update_paces_from_critical_segments(self, critical_segments=None):
        """
        Updates 
        """
        if critical_segments:
            self.critical_segments = critical_segments
        self.total_paces = len(self.critical_segments)

        for j in range(self.total_paces):
            low = self.critical_segments[j]
            high = self.get_n_segments() if (j == self.total_paces - 1) else self.critical_segments[j+1]
            pace = self.weighted_paces[low, high]
            self.true_paces_full[low:high] = pace
            self.true_paces_abbrev[j] = pace

            # time calculations
            end_dist = self.race_course.end_distances[high-1]
            start_dist = self.race_course.start_distances[low]
            elapsed_dist = end_dist - start_dist
            self.elapsed_dists[j] = elapsed_dist
            self.true_seg_times[j] = pace * elapsed_dist
        
    def get_pace_per_mile(self, paces):
        """Takes in a full list of pace segments and returns an array of paces per mile.
        """
        assert len(paces) == self.get_n_segments(), 'Pacing plan must have a pace for each segment'
        assert isinstance(paces, np.ndarray), 'Pacing plan must be a numpy array'

        pace_per_mile = np.ones(int(np.ceil(self.race_course.total_distance))) * -1
        n_mile_markers = math.ceil(self.race_course.total_distance)
        mile_markers = np.argwhere(self.race_course.end_distances - np.floor(self.race_course.end_distances) - self.race_course.segment_lengths <= 0)
        mile_markers = mile_markers.reshape(n_mile_markers,)
        overflow = 0
        total_time = 0

        for m in range(n_mile_markers):
            if m == 0:
                i = 0
            else: 
                i = mile_markers[m] + 1
            if m == n_mile_markers -1:
                j = self.race_course.n_segments-1
            else:
                j = mile_markers[m+1]

            time = overflow + np.dot(self.race_course.segment_lengths[i:j], paces[i:j])

            if m != n_mile_markers - 1:
                overflow_distance = self.race_course.end_distances[j] - (m+1) # distance from last segment that we exclude
                incl_distance = self.race_course.segment_lengths[j] - overflow_distance
                incl_time = incl_distance*paces[j]
                overflow = overflow_distance * paces[j]
                time += incl_time
                pace_per_mile[m] = time
            else:
                pace_per_mile[m] = time / (overflow_distance + np.sum(self.race_course.segment_lengths[i:j]))
            total_time += time

        return pace_per_mile
    
    def get_text_plan_full(self):
        """
        Generates a .txt pacing plan that explicitly statements the pace run at every segment.
        """
        display_txt = ""
        for i in range(self.get_n_segments()):
            lat = self.race_course.lats[i]
            lon = self.race_course.lons[i]
            pace = self.true_paces_full[i]
            dist = self.race_course.segment_lengths[i]
            time = pace * dist
            elevation = self.race_course.start_elevations[i] # feet
        
            display_txt += f"{i}, {pace}, {lat}, {lon}, {elevation}, {dist}, {time} \n"
        return display_txt
    
    def get_text_plan_abbrev(self):
        """
        Generates a simplified .txt pacing plan that includes just the different pace segments.
        TODO: rename as gen_plan_per_pace_segment
        """
        display_txt = ""

        header = f'{self.race_course.course_name}: {self.target_time} minute plan'
        display_txt += header + '\n\n'

        for i, pace in enumerate(self.true_paces_abbrev):
            lat_lon_txt = ''
            if self.race_course is type(race_course.RealRaceCourse):
                lat_lon_txt = f' @ ({self.race_course.lats[i]},{self.race_course.lons[i]})'
            distance_duration = self.elapsed_dists[i]
            start_distance = self.race_course.start_distances[self.critical_segments[i]]
            txt = f"{i}: {start_distance:.2f} mi\t{utils.get_pace_display_text(pace)}/mile for {distance_duration:.2f} mi{lat_lon_txt}"
            display_txt += txt + '\n'
        
        display_txt += f"\nTotal time: {self.target_time :.2f}"

        return display_txt
    
    def gen_text_plan_per_mile(self):
        """
        Returns a .csv pace plan in the following schema:
        [mile_idx], [pace], [time_per_mile], [elapsed_time], [distance (miles)]
        """
        n_mile_markers = math.ceil(self.race_course.total_distance)
        distance = np.ones(n_mile_markers)
        distance[-1] = self.race_course.total_distance - n_mile_markers + 1
        time_per_mile = np.multiply(distance, self.pace_per_mile)
        elapsed_time = np.cumsum(time_per_mile)
        
        display_txt = ""

        header = f'{self.race_course.course_name}: {self.target_time} minute plan'
        display_txt += header + '\n\n'

        column_titles = '[mile_idx], [pace], [time_per_mile], [elapsed_time], [distance (miles)]'
        display_txt += column_titles +'\n'

        for i in range(n_mile_markers):
            pace = self.pace_per_mile[i]
            txt = f"{i} mi \t{utils.get_pace_display_text(pace)}/mile \t {time_per_mile[i]} min \t {elapsed_time[i]} min \t {distance[i]} mi"
            display_txt += txt + '\n'
        
        display_txt += f"\nTotal time: {self.true_total_time :.2f}"
        
        return display_txt
    
    def gen_text_plan(self, file_path : str, export_mode : ExportMode):
        if export_mode == ExportMode.ABBREV:
            txt = self.get_text_plan_abbrev()
        elif export_mode == ExportMode.FULL:
            txt = self.get_text_plan_full()
        elif export_mode == ExportMode.PER_MILE:
            txt = self.gen_text_plan_per_mile()

        with open(file_path, 'w') as file:
            file.write(txt)

    def gen_geojson_full(self, file_path, loop):
        # Initialize the base structure of the GeoJSON
        geojson_data = {
            "type": "FeatureCollection",
            "features": []
        }
        
        # Loop through each segment and create a new feature for each one
        all_changes = self.critical_segments
        if (all_changes[-1] != self.get_n_segments()):
            all_changes = np.append(all_changes, self.get_n_segments())

        for start, end in zip(all_changes, all_changes[1:]):
            pace = self.true_paces_full[start]
            lats = self.race_course.lats[start:end+1]
            lons = self.race_course.lons[start:end+1]
            elevations = self.race_course.elevations[start:end+1]

            coords = np.stack((lons,lats, elevations))
            coords = coords.T.tolist()

            if(end == self.get_n_segments() and loop):
                coords.append([self.race_course.lons[0],self.race_course.lats[0],self.race_course.elevations[0]])

            # Create a feature for each segment
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": coords
                },
                "properties": {
                    "pace": pace  # Add pace property
                }
            }
            
            # Append the feature to the features array in GeoJSON
            geojson_data["features"].append(feature)

        with open(file_path, 'w') as geojson_file:
            json.dump(geojson_data, geojson_file, indent=4)

        return geojson_data
    
    def gen_geojson_abbrev(self, file_path):
        """
        Generates a simplified .json pacing plan that includes just the different pace segments.
        """
        segments = []

        for i, pace in enumerate(self.true_paces_abbrev):
            segment = {
                "segment_num": i,
                "start_distance": "{:.2f}".format(self.race_course.start_distances[self.critical_segments[i]]),
                "pace": utils.get_pace_display_text(pace),
                "distance": "{:.2f}".format(self.elapsed_dists[i])
            }

            # Include latitude and longitude if race_course is of type RealRaceCourse
            if self.race_course is type(race_course.RealRaceCourse):
                segment["lat_lon"] = {
                    "latitude": self.race_course.lats[i],
                    "longitude": self.race_course.lons[i]
                }

            segments.append(segment)

        result = {
            "course_name": self.race_course.course_name,
            "target_time": self.target_time,
            "segments": segments,
            "total_time": self.target_time
        }

        with open(file_path, 'w') as geojson_file:
            json.dump(result, geojson_file, indent=4)
        return result
    
    def gen_geojson_per_mile(self, file_path):
        """
        Returns a .json pace plan in the following schema:
        [mile_idx], [pace], [time_per_mile], [elapsed_time], [distance (miles)]
        """
        n_mile_markers = math.ceil(self.race_course.total_distance)
        distance = np.ones(n_mile_markers)
        distance[-1] = self.race_course.total_distance - n_mile_markers + 1
        time_per_mile = np.multiply(distance, self.pace_per_mile)
        elapsed_time = np.cumsum(time_per_mile)
        
        segments = []
        for i in range(n_mile_markers):
            segment = {
                "mile_index": i,
                "pace_per_mile": utils.get_pace_display_text(self.pace_per_mile[i]),
                "time_per_mile": time_per_mile[i],
                "elapsed_time": elapsed_time[i],
                "distance": distance[i]
            }
            segments.append(segment)

        result = {
            "course_name": self.race_course.course_name,
            "target_time": self.target_time,
            "segments": segments,
            "total_time": self.true_total_time
        }

        with open(file_path, 'w') as geojson_file:
            json.dump(result, geojson_file, indent=4)
        return result
    
    def gen_pace_chart(self, file_path, incl_elevation=True, incl_opt_paces=False, incl_true_paces=True, incl_opt_pace_per_mile=False, incl_true_pace_per_mile=False):
        if not (incl_elevation or incl_opt_paces or incl_true_paces or incl_opt_pace_per_mile or incl_true_pace_per_mile):
            raise ValueError("at least one of incl_elevation or incl_opt_paces or incl_true_paces or incl_opt_pace_per_mile or incl_true_pace_per_mile must be True")

        fig,ax = plt.subplots()
        fig.set_figwidth(20)

        x = np.insert(self.race_course.end_distances, 0,0)
        y_elevations = self.race_course.elevations
        alpha = 1 if incl_elevation else 0
        ax.plot(x, y_elevations, label ='elevation', color='blue', alpha=alpha)

        ax.set_xlabel('distance (miles)')
        ax.set_ylabel('elevation (feet)')

        ax2 = ax.twinx()
        ax2.set_ylabel('pace (min/mile)')

        alpha = .4 if incl_opt_paces else 0
        y_optimal_paces = np.append(self.optimal_paces, self.optimal_paces[-1])
        ax2.step(x, y_optimal_paces, label='optimal paces', color='orange', alpha=alpha, where='post')
            
        if incl_opt_pace_per_mile:
            opt_pace_per_mile = self.get_pace_per_mile(self.optimal_paces)
            y_optimal_pace_per_mile = np.append(opt_pace_per_mile, opt_pace_per_mile[-1])
            x_mile_markers = [i for i in range(0, len(y_optimal_pace_per_mile) - 1)] + [self.race_course.total_distance]
            ax2.step(x_mile_markers, y_optimal_pace_per_mile, label='optimal pace per mile', color='green', alpha=0.4, where='post')

            for i, xy in enumerate(zip(x_mile_markers[:-1], y_optimal_pace_per_mile[:-1])):
                pace = y_optimal_pace_per_mile[i]
                ax2.annotate(f'{utils.get_pace_display_text(pace)}', xy, xytext=(10,10), textcoords='offset pixels')
            
        if incl_true_paces:
            y_true_paces = np.append(self.true_paces_full, self.true_paces_full[-1])
            ax2.step(x, y_true_paces, label='recommended paces', color='red', where='post')

            for i, xy in enumerate(zip(x, self.true_paces_full)):
                if i in self.critical_segments:
                    pace = self.true_paces_full[i]
                    ax2.annotate(f'{utils.get_pace_display_text(pace)}', xy, xytext=(10,10), textcoords='offset pixels')
        
        if incl_true_pace_per_mile:
            true_pace_per_mile = self.get_pace_per_mile(self.true_paces_full)
            y_optimal_pace_per_mile = np.append(true_pace_per_mile, true_pace_per_mile[-1])
            x_mile_markers = [i for i in range(0, len(y_optimal_pace_per_mile) - 1)] + [self.race_course.total_distance]
            ax2.step(x_mile_markers, y_optimal_pace_per_mile, label='optimal pace per mile', color='brown', alpha=0.7, where='post')

            for i, xy in enumerate(zip(x_mile_markers[:-1], y_optimal_pace_per_mile[:-1])):
                pace = y_optimal_pace_per_mile[i]
                ax2.annotate(f'{utils.get_pace_display_text(pace)}', xy, xytext=(10,10), textcoords='offset pixels')

        fig.legend(loc="upper left", bbox_to_anchor=(0.125, 0.875))
        ax.set_title(f'{self.race_course.course_name} Pacing Plan')
        plt.savefig(file_path, bbox_inches='tight',dpi=300)

class PacingPlanStatic(PacingPlan):
    """Pre-computed pacing plan based off fixed target_time and total_paces"""
    def __init__(self, race_course : race_course.RaceCourse, target_time : float, total_paces : int):
        super().__init__(race_course, target_time, total_paces)

        # Populated after pace recommendations are calculated
        self.critical_segments = np.ones(self.total_paces).astype(int)*-1
        self.true_paces_abbrev = np.ones(self.total_paces).astype(float) * -1 
        self.true_paces_full = np.ones(self.race_course.n_segments).astype(float) * -1
        self.true_seg_times = np.ones(self.total_paces).astype(float) * -1
        self.elapsed_dists = np.ones(self.total_paces).astype(float) * -1
        self.pace_per_mile = np.ones(int(np.ceil(self.race_course.total_distance))) * -1
        self.true_total_time = 0
        
    def get_segment_lengths(self):
        return self.race_course.segment_lengths
    
    def get_n_segments(self):
        return self.race_course.n_segments

    def get_recommended_paces(self):
        return self.true_paces_full

    @abstractmethod
    def _calculate_recommendations(self, verbose) -> np.ndarray:
        """
        Returns pacing plan in the form of an array of paces for each segment.
        """
        pass

    def calculate_recommendations(self, verbose=False, eps=1e-2):
        """
        Calculates the pacing plan and populates the necessary attributes
        """
        paces = self._calculate_recommendations(verbose)
        assert isinstance(paces, np.ndarray), 'Pacing plan must be a numpy array'
        assert len(paces) == self.get_n_segments(), 'Pacing plan must have a pace for each segment'

        self.true_seg_times = self.get_segment_lengths() * paces
        self.true_total_time = sum(self.true_seg_times)
        assert abs(self.true_total_time - self.target_time) < eps, f'Total time of pacing plan must equal target time: {self.true_total_time:.3f} = {self.target_time:.3f}'

        self.true_paces_full = paces
        self.true_paces_abbrev = utils.gen_abbrev_paces(paces)
        self.critical_segments = utils.gen_critical_segments(paces)
        self.elapsed_dists = utils.gen_elapsed_distances(paces, self.race_course.start_distances, self.race_course.total_distance)
        self.pace_per_mile = self.get_pace_per_mile(self.true_paces_full)
        self.true_total_time = np.sum(self.true_seg_times)

        return paces

    def __repr__(self, verbose=True):
        assert self.true_paces_full.all() != -1, "Pacing plan has not been calculated yet"
        if verbose:
            return self.get_text_plan_full()
        else:
            return self.get_text_plan_abbrev()

class PacingPlanBF(PacingPlanStatic):
    def __init__(self,race_course : race_course.RaceCourse, target_time, total_paces):
        super().__init__(race_course, target_time, total_paces)
        n = self.get_n_segments()
        self.MIN_SEGMENT_LENGTH = 3 # TODO: test different values of this parameter; dynamically change its initialization based off the race course
        self.LOSS = np.ones((n, n+1, total_paces)) * np.inf
        self.OPT = np.ones((n, n+1, total_paces)).astype(int)*-1
        self.cached_m_paces = 0

    def get_idxs(self,i,k,a, verbose=False):
        """
        Returns the set of indices that represent the segments we change pace on for a pacing plan 
        for interval [i,k) with [a] pace changes remaining.
        """
        if verbose:
            print(f"range [{i},{k}) with {a} pace changes")
        if a == 0:
            return {i}
        j = self.OPT[i,k,a]
        if verbose:
            print(f"split on index {j}\n")
        right = self.get_idxs(j,k,a-1, verbose)
        right.add(i)
        return right
    
    def backtrack_solution(self):
        n = self.get_n_segments()
        m_paces = self.total_paces

        # list of segment indices where we change the paces
        self.critical_segments = np.array(sorted(self.get_idxs(0,n, self.total_paces-1))).astype(int)
        
        self.update_paces_from_critical_segments()
        
    def calculate_brute_force(self, verbose=True):
        n = self.get_n_segments()
        
        if self.cached_m_paces == 0:
            # TODO: rewrite using numpy vectorized functions
            for i in range(n):
                for j in range(i+1, n+1):
                    loss = np.sum(self.loss_method(self.optimal_paces[i:j]-self.weighted_paces[i,j]))
                    self.LOSS[i,j,0] = loss

        for a in range(max(1, self.cached_m_paces), self.total_paces):
            if verbose:
                print(f'PROGRESSED TO A = {a}')
            for i in range(n):
                # k >= i + number of pace changes + 1 
                for k in range(i+(a+1)*self.MIN_SEGMENT_LENGTH, n+1):
                    best_j = -1 
                    lowest_loss = np.inf
                    
                    for j in range(i+self.MIN_SEGMENT_LENGTH,k - self.MIN_SEGMENT_LENGTH + 1):
                        loss = self.LOSS[i,j,0] + self.LOSS[j,k,a-1]
                        if loss < lowest_loss:
                            lowest_loss = loss
                            best_j = j 
                    
                    self.LOSS[i,k,a] = lowest_loss
                    self.OPT[i,k,a] = int(best_j)
        
        self.cached_m_paces = self.total_paces

    def change_total_paces(self, new_m_paces):
        if new_m_paces > self.total_paces:
            self.LOSS = np.pad(self.LOSS, ((0,0), (0,0), (0,new_m_paces-self.total_paces)), 'constant', constant_values=np.inf)
            self.OPT = np.pad(self.OPT, ((0,0), (0,0), (0,new_m_paces-self.total_paces)), 'constant', constant_values=-1)
        
        self.critical_segments = np.ones(new_m_paces).astype(int)*-1
        self.true_paces_abbrev = np.ones(new_m_paces).astype(float) * -1 
        self.elapsed_dists = np.ones(new_m_paces).astype(float) * -1
        self.true_seg_times = np.ones(new_m_paces).astype(float) * -1

        self.total_paces = new_m_paces

    def _calculate_recommendations(self, verbose=False):
        if self.total_paces > self.cached_m_paces:
            self.calculate_brute_force(verbose)
        self.backtrack_solution()
        self.pace_per_mile = self.get_pace_per_mile(self.true_paces_full)
        return self.true_paces_full

class PacingPlanBFSquare(PacingPlanBF):
    def __init__(self, race_course : race_course.RaceCourse, target_time, total_paces):
        super().__init__(race_course, target_time, total_paces)
        self.loss_method = np.square

class PacingPlanBFAbsolute(PacingPlanBF):
    def __init__(self, race_course : race_course.RaceCourse, target_time, total_paces):
        super().__init__(race_course, target_time, total_paces)
        self.loss_method = np.abs

class PacingPlanAvgPacePerMile(PacingPlanStatic):
    def __init__(self, race_course, target_time, total_paces):
        super().__init__(race_course, target_time, total_paces)

    def _calculate_recommendations(self, verbose):
        self.pace_per_mile = self.get_pace_per_mile(self.optimal_paces)
        for i in range(self.get_n_segments()):
            mile = int(self.race_course.start_distances[i])
            self.true_paces_full[i] = self.pace_per_mile[mile]
        return self.true_paces_full

class PacingPlanAvgPace(PacingPlanStatic):
    def __init__(self, race_course, target_time, total_paces):
        super().__init__(race_course, target_time, total_paces)

    def _calculate_recommendations(self, verbose):
        avg_pace = self.target_time / self.race_course.total_distance
        self.true_paces_full[:] = avg_pace
        return self.true_paces_full

class PacingPlanSegmenting(PacingPlanStatic):
    MIN_HILL_DISTANCE = 350*utils.Conversions.METERS_TO_MILES.value # 350 Meters in Miles
    MIN_HILL_HEIGHT = 30    # Feet
    MIN_UPHILL_GRADE = 2    # Grade (smoothed)
    MIN_DOWNHILL_GRADE = 3  # Grade (smoothed)
    MIN_SEGMENT_LENGTH = .25    # Miles
    
    def __init__(self, race_course, target_time, total_paces):
        super().__init__(race_course, target_time, total_paces)
        
    def _calculate_recommendations(self, verbose):
        self.race_course.smoothen_segments(smoothen="gaussian") # Window should be 3
        grades = self.race_course.grades
        start_distances = self.race_course.start_distances
        end_distances = self.race_course.end_distances
        elevations = self.race_course.elevations
        distances = self.race_course.segment_lengths
        
        uphills, downhills = PacingPlanSegmenting.detect_hills(grades, start_distances, end_distances, elevations, 
            PacingPlanSegmenting.MIN_UPHILL_GRADE, PacingPlanSegmenting.MIN_DOWNHILL_GRADE, PacingPlanSegmenting.MIN_HILL_DISTANCE, PacingPlanSegmenting.MIN_HILL_HEIGHT)

        segments = PacingPlanSegmenting.get_spanning_segments(distances, elevations*utils.Conversions.FEET_TO_MILES.value, uphills, downhills, PacingPlanSegmenting.MIN_SEGMENT_LENGTH)
        self.segments = segments
        for segment in segments:
            start, end = segment
            self.true_paces_full[start:end+1] = utils.calculate_segment_pace(start, end, distances, self.optimal_paces)
        return self.true_paces_full

    @staticmethod
    def detect_hills(grades, start_distances, end_distances, elevations, uphill_cutoff, downhill_cutoff, min_length, min_height):    
        significant_uphills = (grades >= uphill_cutoff)
        significant_downhills = (grades <= -downhill_cutoff)

        uphill_segments = PacingPlanSegmenting.find_continuous_segments(significant_uphills, grades)
        downhill_segments = PacingPlanSegmenting.find_continuous_segments(significant_downhills, -grades)
        
        filtered_uphill_segments = PacingPlanSegmenting.filter_short_segments(uphill_segments, min_length, start_distances, end_distances)
        filtered_downhill_segments = PacingPlanSegmenting.filter_short_segments(downhill_segments, min_length, start_distances, end_distances)
        
        filtered_uphill_segments = PacingPlanSegmenting.filter_short_hills(filtered_uphill_segments, min_height, elevations)
        filtered_downhill_segments = PacingPlanSegmenting.filter_short_hills(filtered_downhill_segments, min_height, elevations)

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
                    adjusted_start = PacingPlanSegmenting.adjust_point(start, grades, -1)
                    adjusted_end = PacingPlanSegmenting.adjust_point(i - 2, grades, 1)
                    segments.append((adjusted_start, adjusted_end))
                    start = None
                    i = adjusted_end + 1
                    
        if start is not None:
            adjusted_start = PacingPlanSegmenting.adjust_point(start, grades, -1)
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

        return PacingPlanSegmenting.merge_filler_segments(distances, elevations, filler_segments, full_course_segments, min_segment_length)

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
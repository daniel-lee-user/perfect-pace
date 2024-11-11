import numpy as np
import cvxpy as cp
import matplotlib.pyplot as plt
import race_course
from abc import ABC, abstractmethod
import json
import utils
import math

# TODO: create export function for pacing plan

# GENERAL NOTE: for now, all units below are in feet for elevation and miles for distance (for readability). 
# later, we want to be able to work in any metric or imperial units.

class PacingPlan(ABC):
    def __init__(self, race_course : race_course.RaceCourse, target_time, total_paces):
        self.target_time = target_time
        self.race_course = race_course
        self.current_m_paces = total_paces
        grades = self.race_course.grades
        adjustments = utils.get_pace_adjustments(grades)
        self.base_pace = (self.target_time - np.dot(adjustments, self.get_distances())) / np.sum(self.get_distances())
        self.optimal_paces = np.full(grades.shape, self.base_pace) + adjustments
        self.optimal_seg_times = np.multiply(self.get_distances(), self.optimal_paces)

        # Populated after pace recommendations are calculated
        self.critical_segments = np.ones(self.current_m_paces).astype(int)*-1
        self.true_paces_abbrev = np.ones(self.current_m_paces).astype(float) * -1 
        self.true_paces_full = np.ones(self.race_course.n_segments).astype(float) * -1
        self.true_seg_times = np.ones(self.current_m_paces).astype(float) * -1
        self.elapsed_dists = np.ones(self.current_m_paces).astype(float) * -1
        self.pace_per_mile = np.ones(int(np.ceil(self.race_course.total_distance))) * -1
    
    def get_distances(self):
        return self.race_course.distances
    
    def get_n_segments(self):
        return self.race_course.n_segments

    def get_recommended_paces(self):
        return self.true_paces_full

    def change_total_paces(self, new_m_paces):
        self.total_paces = new_m_paces

    def gen_pace_per_mile(self, paces):
        assert len(paces) == self.get_n_segments(), 'Pacing plan must have a pace for each segment'
        assert isinstance(paces, np.ndarray), 'Pacing plan must be a numpy array'

        n_mile_markers = math.ceil(self.race_course.total_distance)
        mile_markers = np.argwhere(self.race_course.end_distances - np.floor(self.race_course.end_distances) - self.race_course.distances <= 0)
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

            time = overflow + np.dot(self.race_course.distances[i:j], paces[i:j])

            if m != n_mile_markers - 1:
                overflow_distance = self.race_course.end_distances[j] - (m+1) # distance from last segment that we exclude
                incl_distance = self.race_course.distances[j] - overflow_distance
                incl_time = incl_distance*paces[j]
                overflow = overflow_distance * paces[j]
                time += incl_time

                self.pace_per_mile[m] = time

            else:
                self.pace_per_mile[m] = time / (overflow_distance + np.sum(self.race_course.distances[i:j]))
            total_time += time
        # assert (np.isclose(total_time, self.true_total_time))

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

        self.true_seg_times = self.get_distances() * paces
        assert abs(sum(self.true_seg_times) - self.target_time) < eps, f'Total time of pacing plan must equal target time: {sum(self.true_seg_times):.3f} = {self.target_time:.3f}'

        self.true_paces_full = paces
        self.true_paces_abbrev = utils.gen_abbrev_paces(paces)
        self.critical_segments = utils.gen_critical_segments(paces)
        self.elapsed_dists = utils.gen_elapsed_distances(paces, self.race_course.start_distances, self.race_course.total_distance)

        return paces
    
    def gen_full_text(self):
        """
        Generates a .txt pacing plan that explicitly statements the pace run at every segment.
        """
        display_txt = ""
        for i in range(self.get_n_segments()):
            lat = self.race_course.lats[i]
            lon = self.race_course.lons[i]
            pace = self.true_paces_full[i]
            dist = self.race_course.distances[i]
            time = pace * dist
            elevation = self.race_course.elevations[i] # feet
        
            display_txt += f"{i}, {pace}, {lat}, {lon}, {elevation}, {dist}, {time} \n"
        return display_txt
    
    def gen_geojson(self, file_path, loop):
        # Initialize the base structure of the GeoJSON
        geojson_data = {
            "type": "FeatureCollection",
            "features": []
        }
        
        # Loop through each segment and create a new feature for each one
        all_changes = self.critical_segments
        if(all_changes[len(all_changes)-1] != self.get_n_segments()-1):
            all_changes = np.append(all_changes, self.get_n_segments()-1)
        start_idx = all_changes[0] # assuming changes always starts at 0
        for i in range(1, len(all_changes)):
            all_segments = []
            for j in range(start_idx, all_changes[i]+1):
                all_segments.append(self.race_course.segments[j])
            
            pace = self.true_paces_full[start_idx]
            
            coords = [[seg.start_lat, seg.start_lon, seg.start_ele] for seg in all_segments]
            if(i == len(all_changes)-1 and loop):
                # if last segment and loop is true
                first_seg = self.race_course.segments[0]
                coords.append([first_seg.start_lon, first_seg.start_lat, first_seg.start_ele])

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
            start_idx = all_changes[i]
        with open(file_path, 'w') as geojson_file:
            json.dump(geojson_data, geojson_file, indent=4)
        return geojson_data

    def gen_abbrev_plan(self):
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
    
    """Returns a .csv pace plan in the following schema:
     [mile_idx], [pace], [time_per_mile], [elapsed_time], [distance (miles)]
       """
    def gen_plan_per_mile(self, file_path, use_csv=False):
        n_mile_markers = math.ceil(self.race_course.total_distance)
        distance = np.ones(n_mile_markers)
        distance[-1] = self.race_course.total_distance - n_mile_markers + 1
        time_per_mile = np.multiply(distance, self.pace_per_mile)
        elapsed_time = np.cumsum(time_per_mile)

        if use_csv:
            output = np.stack((np.arange(n_mile_markers), self.pace_per_mile, time_per_mile, elapsed_time, distance), axis=1)
            np.savetxt(file_path, output, delimiter=',')
            return output
        
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
        
        with open(file_path, 'w') as f:
            f.write(display_txt)
        return display_txt

    def gen_pace_chart(self, file_path, incl_elevation=True, incl_opt_paces=False, incl_true_paces=True, incl_opt_pace_per_mile=False, incl_true_pace_per_mile=False):
        if not (incl_elevation or incl_opt_paces or incl_true_paces or incl_opt_pace_per_mile or incl_true_pace_per_mile):
            raise ValueError("at least one of incl_elevation or incl_opt_paces or incl_true_paces or incl_opt_pace_per_mile or incl_true_pace_per_mile must be True")

        fig,ax = plt.subplots()
        fig.set_figwidth(20)

        x = np.insert(self.race_course.end_distances, 0,0)
        y_elevations = np.append(self.race_course.elevations, self.race_course.end_elevations[-1])
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
            self.gen_pace_per_mile(self.optimal_paces)
            y_optimal_pace_per_mile = np.append(self.pace_per_mile, self.pace_per_mile[-1])
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
            self.gen_pace_per_mile(self.true_paces_full)
            y_optimal_pace_per_mile = np.append(self.pace_per_mile, self.pace_per_mile[-1])
            x_mile_markers = [i for i in range(0, len(y_optimal_pace_per_mile) - 1)] + [self.race_course.total_distance]
            ax2.step(x_mile_markers, y_optimal_pace_per_mile, label='optimal pace per mile', color='brown', alpha=0.7, where='post')

            for i, xy in enumerate(zip(x_mile_markers[:-1], y_optimal_pace_per_mile[:-1])):
                pace = y_optimal_pace_per_mile[i]
                ax2.annotate(f'{utils.get_pace_display_text(pace)}', xy, xytext=(10,10), textcoords='offset pixels')

        fig.legend(loc="upper left", bbox_to_anchor=(0.125, 0.875))
        ax.set_title(f'{self.race_course.course_name} Pacing Plan')
        plt.savefig(file_path, bbox_inches='tight',dpi=300)

    def __repr__(self, verbose=True):
        assert self.true_paces_full.all() != -1, "Pacing plan has not been calculated yet"
        if verbose:
            return self.gen_full_text()
        else:
            return self.gen_abbrev_plan()

class PacingPlanBruteForce(PacingPlan):
    def __init__(self,race_course : race_course.RaceCourse, target_time, total_paces):
        super().__init__(race_course, target_time, total_paces)
        n = self.get_n_segments()
        self.MIN_SEGMENT_LENGTH = 5 # TODO: test different values of this parameter; dynamically change its initialization based off the race course
        self.WP = np.zeros((n,n+1))
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
        m_paces = self.current_m_paces

        # list of segment indices where we change the paces
        self.critical_segments = np.array(sorted(self.get_idxs(0,n, self.current_m_paces-1))).astype(int)

        for j in range(m_paces):
            low = self.critical_segments[j]
            high = n if (j == m_paces - 1) else self.critical_segments[j+1]
            pace = self.WP[low, high]
            self.true_paces_full[low:high] = pace
            self.true_paces_abbrev[j] = pace

            # time calculations
            end_dist = self.race_course.end_distances[high-1]
            start_dist = self.race_course.start_distances[low]
            elapsed_dist = end_dist - start_dist
            self.elapsed_dists[j] = elapsed_dist
            self.true_seg_times[j] = pace * elapsed_dist
        
        self.true_total_time = np.sum(self.true_seg_times)

    def calculate_brute_force(self, verbose=True):
        n = self.get_n_segments()
        
        if self.cached_m_paces == 0:
            # TODO: rewrite using numpy vectorized functions
            for i in range(n):
                for j in range(i+1, n+1):
                    self.WP[i,j] = np.dot(self.optimal_paces[i:j], self.get_distances()[i:j] / sum(self.get_distances()[i:j]))
                    self.LOSS[i,j,0] = np.sum(self.optimal_paces[i:j] - self.WP[i,j])

        for a in range(max(1, self.cached_m_paces), self.current_m_paces):
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
        
        self.cached_m_paces = self.current_m_paces

    def change_total_paces(self, new_m_paces):
        if new_m_paces > self.current_m_paces:
            self.LOSS = np.pad(self.LOSS, ((0,0), (0,0), (0,new_m_paces-self.current_m_paces)), 'constant', constant_values=np.inf)
            self.OPT = np.pad(self.OPT, ((0,0), (0,0), (0,new_m_paces-self.current_m_paces)), 'constant', constant_values=-1)
        
        self.critical_segments = np.ones(new_m_paces).astype(int)*-1
        self.true_paces_abbrev = np.ones(new_m_paces).astype(float) * -1 
        self.elapsed_dists = np.ones(new_m_paces).astype(float) * -1
        self.true_seg_times = np.ones(new_m_paces).astype(float) * -1

        self.current_m_paces = new_m_paces

    def _calculate_recommendations(self, verbose=False):
        if self.current_m_paces > self.cached_m_paces:
            self.calculate_brute_force(verbose)
        self.backtrack_solution()
        self.gen_pace_per_mile(self.true_paces_full)
        return self.true_paces_full
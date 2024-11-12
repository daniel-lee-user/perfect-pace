import numpy as np
from utils import SegmentType, Unit, Conversions, calculate_grade
import warnings
from scipy.ndimage import gaussian_filter1d
import scipy

class SegmentView:
    def __init__(self, segment_type, lats, lons, segment_lengths, elevations, grades=None):
        self.segment_type = segment_type
        self.n_segments = len(segment_lengths)
        self.lats = lats # n_segments + 1
        self.lons = lons # n_segments + 1 
        self.segment_lengths = segment_lengths # n_segments
        
        self.end_distances = np.cumsum(segment_lengths) # n_segments
        self.total_distance = self.end_distances[-1]
        self.distances = np.insert(self.end_distances, 0, 0) # n_segments + 1
        self.start_distances = self.distances[:-1] #n_segments
        
        self.elevations = elevations # n_segments + 1
        self.start_elevations = elevations[:-1]
        self.end_elevations = elevations[1:]
        self.elevation_changes = self.end_elevations - self.start_elevations
        if grades is None:
            self.grades = calculate_grade(self.elevation_changes, segment_lengths) # n_segments
        else:
            self.grades = grades

class SegmentViewMetric(SegmentView):
    def __init__(self, segment_type, lats, lons, segment_lengths, elevations, grades=None, interpolate_func=None):
        super().__init__(segment_type, lats, lons, segment_lengths, elevations, grades)
        self.units = Unit.METRIC # TODO: remove as this is encoded in the class type
        if interpolate_func is None:
            self.interpolate_func = {
                "elevations" : scipy.interpolate.interp1d(self.distances, self.elevations, 'linear'),
                "lats" : scipy.interpolate.interp1d(self.distances, self.lats, 'linear'),
                "lons" : scipy.interpolate.interp1d(self.distances, self.lons, 'linear'),
            }
        else:
            self.interpolate_func = interpolate_func
        
class SegmentViewImperial(SegmentView):
    def __init__(self, view : SegmentViewMetric):
        self.units = Unit.IMPERIAL # TODO: remove as this is encoded in the class type
        segment_lengths = view.segment_lengths * Conversions.METERS_TO_MILES.value
        elevations = view.elevations * Conversions.METERS_TO_FEET.value
        super().__init__(view.segment_type, view.lats, view.lons, segment_lengths, elevations, view.grades)
        
class SegmentViewInterpolated(SegmentViewMetric):
    def __init__(self, view : SegmentViewMetric, should_interpolate, loaded_elevations=None, segment_type=None, full_distances=None, segment_lengths=None):
        if should_interpolate:
            lats = view.interpolate_func["lats"](full_distances)
            lons = view.interpolate_func["lons"](full_distances)
            elevations = view.interpolate_func["elevations"](full_distances)
        else:
            lats = view.lats
            lons = view.lons
            segment_type = view.segment_type
            segment_lengths = view.segment_lengths
            elevations = loaded_elevations
        super().__init__(segment_type, lats, lons, segment_lengths, elevations, grades=None, interpolate_func=view.interpolate_func)
    
class SegmentViewInterpFixed(SegmentViewInterpolated):
    def __init__(self, view: SegmentViewMetric, x_step):
        n_segments = int(view.total_distance / x_step) + 1
        full_distances = np.arange(n_segments+1) * x_step
        full_distances[-1] = view.total_distance
        segment_lengths = np.diff(full_distances)
        segment_type = SegmentType.FIXED_LENGTH
        should_interpolate = True
        super().__init__(view, should_interpolate, loaded_elevations=None, segment_type=segment_type, full_distances=full_distances, segment_lengths=segment_lengths)

class SegmentViewInterpUniform(SegmentViewInterpolated):
    def __init__(self, view: SegmentViewMetric, n_segments):
        x_step = view.total_distance / n_segments
        full_distances = np.arange(n_segments+1) * x_step
        segment_lengths = np.full(n_segments, x_step)
        segment_type = SegmentType.UNIFORM
        should_interpolate = True
        super().__init__(view, should_interpolate, loaded_elevations=None, segment_type=segment_type, full_distances=full_distances, segment_lengths=segment_lengths)

class SegmentViewSmoothed(SegmentViewInterpolated):
    def __init__(self, view: SegmentViewInterpolated, new_elevations):
        super().__init__(view, should_interpolate=False, loaded_elevations=new_elevations)
        
class SegmentViewSmoothedBox(SegmentViewSmoothed):
    def __init__(self, view: SegmentViewInterpolated, window_distance=100, min_window_size=3):
        seg_length = view.segment_lengths[0]
        window_size = max(int(window_distance / seg_length), 1)
        window_size -= window_size % 2 == 0 # ensure odd-sized kernel
        if window_size < min_window_size:
            
            message = f"View {window_size} is not high-resolution enough to apply smoothing, segment_length is {seg_length:.2f} m. Manually setting window_size = 3"
            warnings.warn(message)
            window_size = 3
        pad_width = int(window_size / 2)
        padded_elevations = np.pad(view.elevations, pad_width, 'edge')
        kernel = np.ones(window_size) / window_size
        assert(np.isclose(sum(kernel), 1))
        new_elevations = np.convolve(padded_elevations, kernel, 'valid')
        super().__init__(view, new_elevations)

class SegmentViewSmoothedGaussian(SegmentViewSmoothed):
    def __init__(self, view: SegmentViewInterpolated, sigma=1):
        new_elevations = np.array(gaussian_filter1d(view.elevations, sigma))
        super().__init__(view, new_elevations)

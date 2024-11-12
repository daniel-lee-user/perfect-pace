import gpxpy
import gpxpy.gpx
import math
import sys

class Segment:
    def __init__(self, start_lat, start_lon, end_lat, end_lon, start_ele, end_ele):
        self.start_lat = start_lat
        self.start_lon = start_lon
        self.end_lat = end_lat
        self.end_lon = end_lon
        self.start_ele = start_ele
        self.end_ele = end_ele
        self.distance = self.calculate_distance()
        self.elevation_change = self.end_ele - self.start_ele if self.start_ele and self.end_ele else None
        self.slope_angle = self.calculate_slope_angle()
        self.grade = self.calculate_grade()

    def calculate_distance(self):
        radius = 6371
        lat1, lon1, lat2, lon2 = map(math.radians, [self.start_lat, self.start_lon, self.end_lat, self.end_lon])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        distance = radius * c * 1000
        return distance

    def calculate_slope_angle(self):
        if self.distance > 0:
            elevation_change = self.elevation_change
            try:
                horizontal_distance = math.sqrt(self.distance**2 - elevation_change**2) if elevation_change else self.distance
            except:
                horizontal_distance = 0
            return math.atan2(elevation_change, horizontal_distance) * (180 / math.pi)
        return None
    
    def calculate_grade(self):
        if self.distance == 0:
            return 0
        return self.elevation_change / self.distance * 100

    def __repr__(self):
        return f"Segment(Start: ({self.start_lat}, {self.start_lon}), End: ({self.end_lat}, {self.end_lon}), " \
               f"Distance: {self.distance:.2f} meters, Elevation Change: {self.elevation_change:.2f}, " \
               f"Slope Angle: {self.slope_angle:.2f} degrees), " \
               f"Grade: {self.grade:.2f}%"

def parse_gpx(file_path):
        lats = []
        lons = []
        elevations = []

        with open(file_path, 'r') as gpx_file:
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

def parse_gpx_DEPRECATED(file_path):
    with open(file_path, 'r') as gpx_file:
        gpx = gpxpy.parse(gpx_file)
        segments = []
        for track in gpx.tracks:
            for segment in track.segments:
                for i in range(len(segment.points) - 1):
                    start_point = segment.points[i]
                    end_point = segment.points[i + 1]
                    seg = Segment(
                        start_lat=start_point.latitude,
                        start_lon=start_point.longitude,
                        end_lat=end_point.latitude,
                        end_lon=end_point.longitude,
                        start_ele=start_point.elevation,
                        end_ele=end_point.elevation
                    )
                    segments.append(seg)
        return segments

def main():
    if len(sys.argv) != 2:
        print("Usage: python script.py <gpx_file>")
        sys.exit(1)

    file_path = sys.argv[1]
    segments = parse_gpx_DEPRECATED(file_path)

    for segment in segments:
        print(segment)

if __name__ == '__main__':
    main()
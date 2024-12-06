import argparse
import os
import json
import numpy as np
from segmenting_plan import SegmentingPlan, AveragePacePlan, AveragePacePerMilePlan, HillDetectionPlan
from optimal_pacing_calculator import OptimalPacingCalculator
import race_course
import logging
import sys

# Define available segmenting methods
SEGMENTING_METHODS = {
    "AP": AveragePacePlan,
    "APPM": AveragePacePerMilePlan,
    "HILL": HillDetectionPlan
}

def init_parser() -> argparse.ArgumentParser:
    """
    Initializes the command line flag parser for the file.

    Flags:
    [REQUIRED]
    -f, --file  ==> file path of the GPX file to be parsed
    -t, --time  ==> goal time in minutes to complete the course

    [OPTIONAL]
    -o, --output ==> directory for saving the output files (default: results)
    -v, --verbose   ==> verbose mode for debugging
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--file", help="Path to the GPX file", required=True)
    parser.add_argument("-t", "--time", type=int, help="Goal time in minutes to complete the course", required=True)
    parser.add_argument("-o", "--output", help="Output directory (default: current directory)", default="results")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    return parser


def process_segments(course, methods, output_dir, verbose=False):
    """
    Process the segments using the given segmenting methods.
    """
    segments = {}

    for method_name, method_class in methods.items():
        if verbose:
            print(f"Processing with segmenting method: {method_name}")
        plan = method_class(course)
        segment_indices = plan.calculate_segments()
        segments[method_name] = segment_indices

        plot_path = os.path.join(output_dir, f"{method_name}_segments_plot.jpg")
        plan.plot_segments(plot_path, title=f"Segments - {method_name}")
        
        if verbose:
            print(f"Saved plot to {plot_path}")

    return segments

def save_frontend_files(course, target_time, segments, optimal_paces, output_dir):
    """
    Save files needed for frontend session storage.
    """
    # Segment lengths
    segment_lengths = course.segment_lengths.tolist()

    # Coordinates (latitude, longitude, elevation)
    coordinates = [
        [lat, lon, ele] for lat, lon, ele in zip(course.lats, course.lons, course.elevations)
    ]

    # Save preset segments
    preset_segments = segments

    # Prepare data for frontend
    frontend_data = {
        "presetSegments": preset_segments,
        "optimalPaces": optimal_paces,
        "segmentLengths": segment_lengths,
        "coordinates": coordinates,
    }

    # Save each key in separate JSON files for clarity
    for key, value in frontend_data.items():
        file_path = os.path.join(output_dir, f"{key}.json")
        with open(file_path, "w") as json_file:
            json.dump(value, json_file, indent=4)

    print("Frontend files saved successfully.")

def main():
    parser = init_parser()
    args = parser.parse_args()

    file_path = args.file
    target_time = args.time
    verbose = args.verbose

    # Parse the course
    course_name = os.path.basename(file_path).split('.')[0]
    course = race_course.RealRaceCourse(course_name, file_path)

    output_dir = args.output
    if args.output == "results":
        output_dir = os.path.join(output_dir, course_name, 'segments')

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    if verbose:
        print(f"Parsed course: {course_name}")

    # Calculate optimal paces
    optimal_pace_calculator = OptimalPacingCalculator(course, target_time)
    weighted_paces = optimal_pace_calculator.calculate_weighted_paces()

    # Process segmenting methods
    segments = process_segments(course, SEGMENTING_METHODS, output_dir, verbose=verbose)

    # Save frontend files
    save_frontend_files(course, target_time, segments, weighted_paces, output_dir)

    print("Processing complete.")

if __name__ == "__main__":
    main()

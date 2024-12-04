import argparse
import os
import json
import numpy as np
from segmenting_plan import SegmentingPlan, AveragePacePlan, AveragePacePerMilePlan, HillDetectionPlan
from optimal_pacing_calculator import OptimalPacingCalculator
import race_course

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


def main():
    parser = init_parser()
    args = parser.parse_args()

    file_path = args.file
    target_time = args.time
    verbose = args.verbose

    # Parse the course
    course_name = os.path.basename(file_path).split('.')[0]
    course = race_course.RealRaceCourse(course_name, file_path)

    output_dir = os.path.join(args.output, course_name, 'segments')

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    if verbose:
        print(f"Parsed course: {course_name}")

    # Calculate optimal paces
    optimal_pace_calculator = OptimalPacingCalculator(course, target_time)
    weighted_paces = optimal_pace_calculator.calculate_weighted_paces()

    # Save optimal paces to a file
    paces_file_path = os.path.join(output_dir, "optimal_paces.json")
    with open(paces_file_path, "w") as paces_file:
        json.dump(weighted_paces, paces_file, indent=4)

    if verbose:
        print(f"Saved weighted paces to {paces_file_path}")

    # Process segmenting methods
    segments = process_segments(course, SEGMENTING_METHODS, output_dir, verbose=verbose)

    # Save segments to a file
    segments_file_path = os.path.join(output_dir, "segments.json")
    with open(segments_file_path, "w") as segments_file:
        json.dump(segments, segments_file, indent=4)

    if verbose:
        print(f"Saved segments to {segments_file_path}")

    print("Processing complete.")


if __name__ == "__main__":
    main()

from segmenting_plan import *
from race_course import RealRaceCourse
import os
import shutil


SEGMENTING_PLAN_METHODS = {
    "AVG": AveragePacePlan,
    "APPM": AveragePacePerMilePlan,
    "HILL": HillDetectionPlan
}


def main():
    methods = SEGMENTING_PLAN_METHODS
    course_names = ['boston', 'wineglass', 'FH-Fox', 'scurve', 'dodge']
    base_directory = 'data/test-results/'

    # Clean the results directory
    for filename in os.listdir(base_directory):
        file_path = os.path.join(base_directory, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print(f'Failed to delete {file_path}. Reason: {e}')

    # Load race courses
    courses = []
    for name in course_names:
        try:
            file_path = f'data/{name}.gpx'
            course = RealRaceCourse(name, file_path, N_SEGMENTS=200)
            courses.append(course)
        except Exception as e:
            print(f'Error loading {file_path}: {e}')

    # Generate results for each course and method
    for course in courses:
        for method_name, plan_class in methods.items():
            try:
                # Initialize the segmenting plan
                plan = plan_class(course)

                # Create directory for this course and method
                course_directory = os.path.join(base_directory, course.course_name)
                method_directory = os.path.join(course_directory, method_name)
                if not os.path.exists(method_directory):
                    os.makedirs(method_directory)

                # Calculate segments
                plan.calculate_segments()

                # Save the segment graph
                segment_graph_path = os.path.join(method_directory, "segments_plot.png")
                plan.plot_segments(file_path=segment_graph_path,
                                   title=f"{course.course_name} - {method_name} Segments")

                # Log success
                print(f"Generated segment graph for {course.course_name} with {method_name} method.")

            except Exception as e:
                print(f'Error processing {course.course_name} with {method_name}: {e}')


if __name__ == '__main__':
    main()

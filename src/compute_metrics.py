"""
Helper functions for calculating grade metrics, percentages, and deltas.
"""

from typing import Dict, Any, Optional


def calculate_grade_count(csv_row: Dict[str, Any], *grade_keys: str) -> int:
    """
    Calculate total count for one or more grade categories. Necessary for calculating
    total # of A's, B's, and C's & displaying on the grade table

    Args:
        csv_row: `dict` containing grade data
        *grade_keys: Variable number of grade keys (e.g., 'A', 'A+', 'A-')

    Returns:
        Total count across all specified grade keys
    """
    total = 0
    for key in grade_keys:
        try:
            total += int(csv_row[key])
        except (KeyError, ValueError, TypeError):
            continue
    return total


def calculate_total_students(csv_row: Dict[str, Any]) -> int:
    """
    Calculate total number of students from all grade categories. Noticed that 
    the `'Class_Size'` key value does not actually add up to the number of grade counts. So this
    function is used as the denominator to calculate accurate percentages.

    Args:
        csv_row: dict with grade data

    Returns:
        Total student count
    """
    grade_keys = ['A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'D', 'E', 'W']
    return calculate_grade_count(csv_row, *grade_keys)


def calculate_percentage(count: int, total: int) -> str:
    """
    Calculate percentage and format as string.

    Args:
        count: Numerator
        total: Denominator

    Returns:
        Formatted percentage string 
    """
    if total == 0:
        return "0%"
    percentage = (count / total) * 100
    return f"{percentage:.0f}%"


def calculate_grade_delta(
    csv_row_percentage: float,
    agg_grade_percentage: float,
    format_as_percent: bool = True
) -> str:
    """
    Calculate the delta between individual course and aggregate baseline.

    Args:
        csv_row_percentage: percentage for the individual course 
        agg_grade_percentage: aggregate percentage from baseline
        format_as_percent: if true, format as percentage string with % sign

    Returns:
        Delta string with + or - prefix
    """
    delta = csv_row_percentage - agg_grade_percentage

    if format_as_percent:
        delta_pct = delta * 100
        sign = "+" if delta_pct >= 0 else ""
        return f"{sign}{delta_pct:.0f}%"
    else:
        sign = "+" if delta >= 0 else ""
        return f"{sign}{delta:.2f}"


def get_grade_metrics(
    csv_row: Dict[str, Any],
    agg_data: Dict[str, Any],
    grade_category: str
) -> Dict[str, Any]:
    """
    Calculate count, percent, and delta for course grades

    Args:
        csv_row: `dict` containing individual course grade data
        agg_data: `dict` containing aggregate baseline data
        grade_category: One of 'A', 'B', 'C', 'D', 'E'

    Returns:
        `dict` with keys: 'count', 'pct', 'delta'
    """
    # Define which grade keys to include for each category
    grade_mapping = {
        'A': ['A+', 'A', 'A-'],
        'B': ['B+', 'B', 'B-'],
        'C': ['C+', 'C'],
        'D': ['D'],
        'E': ['E']
    }

    if grade_category not in grade_mapping:
        raise ValueError(f"Invalid grade category: {grade_category}")

    grade_keys = grade_mapping[grade_category]

    count = calculate_grade_count(csv_row, *grade_keys)

    # Calculate total students for percentage
    total_students = calculate_total_students(csv_row)

    pct = calculate_percentage(count, total_students)

    # Calculate aggregate percentage from baseline
    grade_percentages = agg_data.get('grade_percentages', {})
    agg_percentage = sum(grade_percentages.get(key, 0.0) for key in grade_keys)

    # Calculate course percentage as decimal for delta calculation
    course_percentage = count / total_students if total_students > 0 else 0.0

    delta = calculate_grade_delta(course_percentage, agg_percentage)

    return {
        'count': count,
        'pct': pct,
        'delta': delta
    }


def get_withdraw_metrics(
    csv_row: Dict[str, Any],
    agg_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Calculate metrics specifically for withdrawals.

    Args:
        csv_row: `dict` containing individual course grade data
        agg_data: `dict` containing aggregate baseline data

    Returns:
        `dict` with keys: 'count', 'pct', 'delta'
    """
    try:
        count = int(csv_row['W'])
    except (KeyError, ValueError, TypeError):
        count = 0

    total_students = calculate_total_students(csv_row)
    pct = calculate_percentage(count, total_students)

    # Calculate aggregate withdrawal percentage
    grade_percentages = agg_data.get('grade_percentages', {})
    agg_percentage = grade_percentages.get('W', 0.0)

    course_percentage = count / total_students if total_students > 0 else 0.0
    delta = calculate_grade_delta(course_percentage, agg_percentage)

    return {
        'count': count,
        'pct': pct,
        'delta': delta
    }


def get_quartile_metrics(agg_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract quartile grade information from aggregate data.

    Args:
        agg_data: `dict` containing aggregate baseline data

    Returns:
        `dict` with keys: 'q1', 'q2' (median), 'q3' and their deltas
    """
    return {
        'q1': agg_data.get('q1_grade', 'N/A'),
        'q2': agg_data.get('median_grade', 'N/A'),
        'q3': agg_data.get('q3_grade', 'N/A'),
    }


def calculate_numeric_delta(
    individual_value: Optional[float],
    aggregate_value: Optional[float],
    decimal_places: int = 2
) -> str:
    """
    Calculate delta between individual and aggregate numeric values.

    Args:
        individual_value: value from pdf eval data `dict`
        aggregate_value: value from aggregate baseline `dict`
        decimal_places: Number of decimal places to round to

    Returns:
        Formatted delta string with + or - prefix
    """
    if individual_value is None or aggregate_value is None:
        return "N/A"

    delta = individual_value - aggregate_value
    sign = "+" if delta >= 0 else ""
    return f"{sign}{delta:.{decimal_places}f}"


def get_gpa_delta(csv_row: Dict[str, Any], agg_data: Dict[str, Any]) -> str:
    """
    Calculate GPA delta between individual course and aggregate baseline.

    Args:
        csv_row: `dict` with the individual course data
        agg_data: `dict` with aggregate baseline data

    Returns:
        Formatted GPA delta string
    """
    try:
        course_gpa = float(csv_row['GPA'])
    except (KeyError, ValueError, TypeError):
        return "N/A"

    agg_gpa = agg_data.get('gpa')
    return calculate_numeric_delta(course_gpa, agg_gpa, decimal_places=2)


def get_course_size_delta(csv_row: Dict[str, Any], agg_data: Dict[str, Any]) -> str:
    """
    Calculate course size delta between individual course and aggregate average.

    Args:
        csv_row: `dict` with the individual course data
        agg_data: `dict` containing aggregate baseline data

    Returns:
        Formatted course size delta string (as integer)
    """
    try:
        course_size = int(csv_row['Class Size'])
    except (KeyError, ValueError, TypeError):
        return "N/A"

    agg_course_size = agg_data.get('course_size_avg')

    if agg_course_size is None:
        return "N/A"

    delta = course_size - agg_course_size
    sign = "+" if delta >= 0 else ""
    return f"{sign}{int(delta)}"


def get_response_rate_delta(pdf_json: Dict[str, Any], agg_data: Dict[str, Any]) -> str:
    """
    Calculate response rate delta between individual course and aggregate.

    Args:
        pdf_json: `dict` containing PDF evaluation data
        agg_data: `dict` containing aggregate baseline data

    Returns:
        Response rate delta string with % sign (currently placeholder)
    """
    # TODO: Implement aggregate response rate tracking in data_handler.py
    # For now, return placeholder since agg_data doesn't include response rates
    return "N/A"


def get_avg_part1_delta(pdf_json: Dict[str, Any], agg_data: Dict[str, Any]) -> str:
    """
    Calculate part 1 avg delta between individual course and aggregate.

    Args:
        pdf_json: `dict` with the PDF evaluation data
        agg_data: `dict` with aggregate baseline data

    Returns:
        Formatted part 1 average delta string
    """
    try:
        course_avg1 = float(pdf_json['eval_info']['avg1'])
    except (KeyError, ValueError, TypeError):
        return "N/A"

    agg_avg1 = agg_data.get('avg_part1')
    return calculate_numeric_delta(course_avg1, agg_avg1, decimal_places=2)


def get_avg_part2_delta(pdf_json: Dict[str, Any], agg_data: Dict[str, Any]) -> str:
    """
    Calculate part 2 avg delta between individual course and aggregate.

    Args:
        pdf_json: `dict` with pdf eval data
        agg_data: `dict` with aggregate baseline data

    Returns:
        Formatted part 2 average delta string
    """
    try:
        course_avg2 = float(pdf_json['eval_info']['avg2'])
    except (KeyError, ValueError, TypeError):
        return "N/A"

    agg_avg2 = agg_data.get('avg_part2')
    return calculate_numeric_delta(course_avg2, agg_avg2, decimal_places=2)


def get_median_grade_delta(csv_row: Dict[str, Any], agg_data: Dict[str, Any]) -> str:
    """
    Calculate median grade delta.

    For now returns placeholder, but could be enhanced to show grade level differences.

    Args:
        csv_row: `dict` with individual course data
        agg_data: `dict` with aggregate baseline data

    Returns:
        Median grade delta (currently placeholder for letter grade comparison)
    """
    # TODO: Calculate individual course median grade & compare it
    return "N/A"
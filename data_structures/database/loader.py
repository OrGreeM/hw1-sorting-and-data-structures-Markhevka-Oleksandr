import csv
from pathlib import Path
from data_structures.database.student import Student
 
def load_students(path: str = "students.csv") -> list[Student]:
    """Load students from a CSV file and return a list of Student objects."""

    file_path = Path(__file__).parent / path

    students = []
    with open(file_path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            students.append(Student(
                m_name=row["m_name"],
                m_surname=row["m_surname"],
                m_email=row["m_email"],
                m_birth_year=int(row["m_birth_year"]),
                m_birth_month=int(row["m_birth_month"]),
                m_birth_day=int(row["m_birth_day"]),
                m_group=row["m_group"],
                m_rating=float(row["m_rating"]),
                m_phone_number=row["m_phone_number"],
            ))
    return students

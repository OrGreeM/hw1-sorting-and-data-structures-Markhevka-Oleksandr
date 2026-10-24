from dataclasses import dataclass

@dataclass
class Student:
    m_name: str           # Name in Ukrainian
    m_surname: str        # Surname in Ukrainian
    m_email: str          # [a-z.]*@student.org is unique
    m_birth_year: int     # 1950..2010
    m_birth_month: int    # 1..12
    m_birth_day: int      # 1..Number of days in m_birth_month
    m_group: str          # [A-Z][A-Z][A-Z]-[0-9][0-9]
    m_rating: float       # 0..100
    m_phone_number: str   # 38(0xx)xx-xx-xxx is unique
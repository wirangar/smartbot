import logging
from src.config import logger

def get_equivalence_parameter(family_members: int) -> float:
    """
    Returns the equivalence parameter based on the number of family members.
    This is based on the official 'Scala di Equivalenza'.
    """
    params = {
        1: 1.00,
        2: 1.57,
        3: 2.04,
        4: 2.46,
        5: 2.85,
    }
    if family_members in params:
        return params[family_members]
    elif family_members > 5:
        return 2.85 + (0.35 * (family_members - 5))
    else:
        return 1.00 # Fallback for invalid numbers, though should be caught earlier

def calculate_isee(income: float, property_value: float, family_members: int) -> float:
    """
    Calculates the ISEE value based on the provided data.
    Formula: (Income + 20% of Property Value) / Equivalence Parameter
    """
    if family_members < 1:
        return 0.0

    ise = income + (property_value * 0.20)
    parameter = get_equivalence_parameter(family_members)

    isee_value = ise / parameter

    logger.info(f"Calculated ISEE: Income={income}, Property={property_value}, Family={family_members}, Parameter={parameter}, ISEE={isee_value}")

    return isee_value

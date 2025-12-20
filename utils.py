from models import CategoryMapping

def auto_categorize(description, user_id):
    """
    Suggests a category based on the description using learned CategoryMapping.
    """
    if not description:
        return 'Other'
    
    keyword = description.lower().strip()
    # Try exact match first
    mapping = CategoryMapping.query.filter_by(user_id=user_id, keyword=keyword).first()
    if mapping:
        return mapping.category
    
    # Try fuzzy match (if any mapping keyword is inside the description)
    all_mappings = CategoryMapping.query.filter_by(user_id=user_id).all()
    for m in all_mappings:
        if m.keyword in keyword:
            return m.category
            
    return 'Other'

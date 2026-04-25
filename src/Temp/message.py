def result_message(message, status_code, result):
    return {"message": message, "status": status_code, "result": result}


def duplicate_field_error_message(message, status_code, field):
    return {
        "message": message,
        "status": status_code,
        "field": field,
    }

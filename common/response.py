from rest_framework import status
from rest_framework.renderers import JSONRenderer


def api_response(
    message="Success", data=None, status_code=status.HTTP_200_OK, success=True
):
    return {
        "success": success,
        "status": status_code,
        "message": message,
        "data": data if data is not None else {},
    }


class CustomJSONRenderer(JSONRenderer):
    charset = "utf-8"

    def flatten_errors(self, errors):
        """Turn DRF serializer errors into readable text."""
        if isinstance(errors, list):
            return " ".join([self.flatten_errors(e) for e in errors])

        if isinstance(errors, dict):
            messages = []
            for field, msgs in errors.items():
                text = self.flatten_errors(msgs)
                if field == "non_field_errors":
                    messages.append(text)
                else:
                    messages.append(f"{field}: {text}")
            return " | ".join(messages)

        return str(errors)

    def render(self, data, accepted_media_type=None, renderer_context=None):
        response = renderer_context.get("response", None)
        status_code = getattr(response, "status_code", 200)

        success = 200 <= status_code < 400
        if success:
            message = "Request successful"
        else:
            message = "Validation error" if status_code == 400 else "Request failed"
        if not success and isinstance(data, dict):
            if "detail" in data:
                message = data.pop("detail")
            elif "error" in data and isinstance(data["error"], dict):
                message = self.flatten_errors(data["error"])
            else:
                message = self.flatten_errors(data)


        if isinstance(data, dict):
            if "message" in data:
                message = data.pop("message")
            elif "detail" in data:
                message = data.pop("detail")
            elif "error" in data and not isinstance(data.get("error"), dict):
               message = data.pop("error")


        if isinstance(data, dict) and "data" in data:
            inner_data = data["data"]
        else:
            inner_data = data if isinstance(data, (dict, list)) else {}

        response_data = api_response(
            message=message,
            data=inner_data,
            status_code=status_code,
            success=success,
        )

        return super().render(response_data, accepted_media_type, renderer_context)

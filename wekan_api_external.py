import requests

def create_wekan_board_external(
    wekan_url: str,
    username: str,
    password: str,
    title: str,
    owner: str = None,
    permission: str = "private",
    color: str = "belize"
) -> dict:
    """
    Create a Wekan board using a direct API call (workaround for environment issues).

    Returns a dict with keys: success, board_id, response, error (if any).
    """
    result = {
        "success": False,
        "board_id": None,
        "response": None,
        "error": None
    }
    try:
        # Authenticate
        login_url = f"{wekan_url.rstrip('/')}/users/login"
        login_resp = requests.post(
            login_url,
            data=f"username={username}&password={password}",
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        if login_resp.status_code != 200:
            result["error"] = f"Auth failed: {login_resp.status_code} - {login_resp.text}"
            return result
        login_data = login_resp.json()
        token = login_data.get("token")
        user_id = login_data.get("id")
        if not token or not user_id:
            result["error"] = f"Auth response missing token or id: {login_data}"
            return result

        # Prepare board creation payload
        boards_url = f"{wekan_url.rstrip('/')}/api/boards"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        payload = {
            "title": title,
            "owner": owner or user_id,
            "permission": permission,
            "color": color
        }
        resp = requests.post(boards_url, headers=headers, json=payload)
        result["response"] = resp.text
        if resp.status_code in [200, 201]:
            data = resp.json()
            result["success"] = True
            result["board_id"] = data.get("_id")
        else:
            result["error"] = f"Board creation failed: {resp.status_code} - {resp.text}"
    except Exception as e:
        result["error"] = str(e)
    return result

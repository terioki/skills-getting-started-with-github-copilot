import pytest
import copy
from fastapi.testclient import TestClient
from src.app import app, activities


# Create a test client for the FastAPI app
client = TestClient(app)


# Store the original state for restoration between tests
ORIGINAL_ACTIVITIES = copy.deepcopy(activities)


@pytest.fixture(autouse=True)
def reset_activities():
    """
    Reset the global activities state before each test.
    This fixture runs automatically (autouse=True) to ensure test isolation.
    """
    # Arrange: Restore original activities state
    activities.clear()
    activities.update(copy.deepcopy(ORIGINAL_ACTIVITIES))
    yield
    # Cleanup: Restore after test completes


class TestRootEndpoint:
    """Tests for GET / endpoint"""

    def test_root_redirects_to_static_index(self):
        """
        Arrange: None (client already configured)
        Act: Make a GET request to root endpoint
        Assert: Verify redirect response to static index
        """
        # Act
        response = client.get("/", follow_redirects=False)

        # Assert
        assert response.status_code == 307
        assert "/static/index.html" in response.headers["location"]


class TestGetActivitiesEndpoint:
    """Tests for GET /activities endpoint"""

    def test_activities_returns_all_activities(self):
        """
        Arrange: None (activities preloaded in fixture)
        Act: Fetch all activities
        Assert: Verify response contains all expected activities with correct structure
        """
        # Act
        response = client.get("/activities")

        # Assert
        assert response.status_code == 200
        data = response.json()
        
        # Verify all activities are present
        expected_activities = [
            "Chess Club",
            "Programming Class",
            "Gym Class",
            "Basketball Team",
            "Tennis Club",
            "Drama Club",
            "Art Studio",
            "Debate Team",
            "Science Club",
        ]
        for activity_name in expected_activities:
            assert activity_name in data

    def test_activity_structure_contains_required_fields(self):
        """
        Arrange: None (activities preloaded)
        Act: Fetch activities and inspect one activity
        Assert: Verify activity has all required fields
        """
        # Act
        response = client.get("/activities")
        data = response.json()

        # Assert
        activity = data["Chess Club"]
        assert "description" in activity
        assert "schedule" in activity
        assert "max_participants" in activity
        assert "participants" in activity
        assert isinstance(activity["participants"], list)

    def test_activities_participants_are_email_strings(self):
        """
        Arrange: None
        Act: Fetch activities
        Assert: Verify participants are email strings
        """
        # Act
        response = client.get("/activities")
        data = response.json()

        # Assert
        for activity_name, activity_details in data.items():
            for participant in activity_details["participants"]:
                assert isinstance(participant, str)
                assert "@" in participant  # Basic email validation


class TestSignupEndpoint:
    """Tests for POST /activities/{activity_name}/signup endpoint"""

    def test_signup_adds_participant_to_activity(self):
        """
        Arrange: Select activity and new email, record initial count
        Act: Post signup request
        Assert: Verify participant added and count increased
        """
        # Arrange
        activity_name = "Chess Club"
        email = "newstudent@mergington.edu"
        initial_count = len(activities[activity_name]["participants"])

        # Act
        response = client.post(f"/activities/{activity_name}/signup?email={email}")

        # Assert
        assert response.status_code == 200
        assert response.json()["message"] == f"Signed up {email} for {activity_name}"
        assert email in activities[activity_name]["participants"]
        assert len(activities[activity_name]["participants"]) == initial_count + 1

    def test_signup_with_nonexistent_activity_returns_404(self):
        """
        Arrange: Use activity name that doesn't exist
        Act: Post signup to nonexistent activity
        Assert: Verify 404 error response
        """
        # Arrange
        activity_name = "Nonexistent Activity"
        email = "student@mergington.edu"

        # Act
        response = client.post(f"/activities/{activity_name}/signup?email={email}")

        # Assert
        assert response.status_code == 404
        assert response.json()["detail"] == "Activity not found"

    def test_signup_duplicate_email_returns_400(self):
        """
        Arrange: Select activity and existing participant email
        Act: Try to sign up existing participant again
        Assert: Verify 400 error for duplicate signup
        """
        # Arrange
        activity_name = "Chess Club"
        email = "michael@mergington.edu"  # Already in Chess Club

        # Act
        response = client.post(f"/activities/{activity_name}/signup?email={email}")

        # Assert
        assert response.status_code == 400
        assert response.json()["detail"] == "Student already signed up for this activity"

    def test_signup_same_email_different_activities_allowed(self):
        """
        Arrange: Select a student and two different activities
        Act: Sign up the same student for both activities
        Assert: Verify both signups succeed (same email allowed across activities)
        """
        # Arrange
        email = "alice@mergington.edu"
        activity1 = "Chess Club"
        activity2 = "Programming Class"

        # Act
        response1 = client.post(f"/activities/{activity1}/signup?email={email}")
        response2 = client.post(f"/activities/{activity2}/signup?email={email}")

        # Assert
        assert response1.status_code == 200
        assert response2.status_code == 200
        assert email in activities[activity1]["participants"]
        assert email in activities[activity2]["participants"]


class TestUnregisterEndpoint:
    """Tests for DELETE /activities/{activity_name}/participants endpoint"""

    def test_unregister_removes_participant_from_activity(self):
        """
        Arrange: Select activity with existing participant, record initial count
        Act: Delete participant from activity
        Assert: Verify participant removed and count decreased
        """
        # Arrange
        activity_name = "Chess Club"
        email = "michael@mergington.edu"  # Already in Chess Club
        initial_count = len(activities[activity_name]["participants"])

        # Act
        response = client.delete(f"/activities/{activity_name}/participants?email={email}")

        # Assert
        assert response.status_code == 200
        assert response.json()["message"] == f"Removed {email} from {activity_name}"
        assert email not in activities[activity_name]["participants"]
        assert len(activities[activity_name]["participants"]) == initial_count - 1

    def test_unregister_nonexistent_activity_returns_404(self):
        """
        Arrange: Use activity that doesn't exist
        Act: Try to unregister from nonexistent activity
        Assert: Verify 404 error response
        """
        # Arrange
        activity_name = "Nonexistent Activity"
        email = "student@mergington.edu"

        # Act
        response = client.delete(f"/activities/{activity_name}/participants?email={email}")

        # Assert
        assert response.status_code == 404
        assert response.json()["detail"] == "Activity not found"

    def test_unregister_participant_not_in_activity_returns_404(self):
        """
        Arrange: Select activity and participant not in that activity
        Act: Try to unregister participant not currently signed up
        Assert: Verify 404 error for participant not found
        """
        # Arrange
        activity_name = "Chess Club"
        email = "emma@mergington.edu"  # Emma is in Programming Class, not Chess Club

        # Act
        response = client.delete(f"/activities/{activity_name}/participants?email={email}")

        # Assert
        assert response.status_code == 404
        assert response.json()["detail"] == "Participant not found for this activity"

    def test_unregister_then_signup_again_succeeds(self):
        """
        Arrange: Remove a participant, then try to sign up again
        Act: Unregister then re-signup same participant
        Assert: Verify both operations succeed independently
        """
        # Arrange
        activity_name = "Chess Club"
        email = "michael@mergington.edu"

        # Act & Assert - Unregister
        response_delete = client.delete(f"/activities/{activity_name}/participants?email={email}")
        assert response_delete.status_code == 200
        assert email not in activities[activity_name]["participants"]

        # Act & Assert - Re-signup
        response_signup = client.post(f"/activities/{activity_name}/signup?email={email}")
        assert response_signup.status_code == 200
        assert email in activities[activity_name]["participants"]

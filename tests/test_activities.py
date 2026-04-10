"""
Comprehensive tests for the Activities Management API.
Tests cover all happy paths and error scenarios.
"""

import pytest


class TestRootEndpoint:
    """Tests for GET / endpoint."""

    def test_root_redirects_to_index(self, client):
        """Test that root endpoint redirects to /static/index.html."""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for GET /activities endpoint."""

    def test_get_all_activities(self, client, sample_activities):
        """Test getting all activities returns correct structure."""
        response = client.get("/activities")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, dict)
        assert len(data) == 9  # All 9 activities
        
        # Verify Chess Club exists with expected structure
        assert "Chess Club" in data
        chess = data["Chess Club"]
        assert chess["description"] == "Learn strategies and compete in chess tournaments"
        assert chess["schedule"] == "Fridays, 3:30 PM - 5:00 PM"
        assert chess["max_participants"] == 12
        assert isinstance(chess["participants"], list)
        assert "michael@mergington.edu" in chess["participants"]

    def test_activity_has_required_fields(self, client, sample_activities):
        """Test that each activity has all required fields."""
        response = client.get("/activities")
        data = response.json()
        
        required_fields = {"description", "schedule", "max_participants", "participants"}
        
        for activity_name, activity_data in data.items():
            assert required_fields.issubset(activity_data.keys()), \
                f"Activity '{activity_name}' missing required fields"


class TestSignupEndpoint:
    """Tests for POST /activities/{activity_name}/signup endpoint."""

    def test_successful_signup(self, client, sample_activities):
        """Test successfully signing up a new student."""
        response = client.post(
            "/activities/Chess Club/signup?email=newstudent@mergington.edu"
        )
        assert response.status_code == 200
        
        result = response.json()
        assert "Signed up" in result["message"]
        assert "newstudent@mergington.edu" in result["message"]
        
        # Verify student was added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "newstudent@mergington.edu" in activities_data["Chess Club"]["participants"]

    def test_signup_increases_participant_count(self, client, sample_activities):
        """Test that signup increases participant count."""
        initial_response = client.get("/activities")
        initial_count = len(initial_response.json()["Programming Class"]["participants"])
        
        client.post("/activities/Programming Class/signup?email=alex@mergington.edu")
        
        after_response = client.get("/activities")
        after_count = len(after_response.json()["Programming Class"]["participants"])
        
        assert after_count == initial_count + 1

    def test_signup_nonexistent_activity(self, client, sample_activities):
        """Test signing up for an activity that doesn't exist."""
        response = client.post(
            "/activities/Nonexistent Activity/signup?email=student@mergington.edu"
        )
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]

    def test_signup_duplicate_student(self, client, sample_activities):
        """Test that the same student cannot sign up twice for the same activity."""
        # Student is already in Chess Club
        response = client.post(
            "/activities/Chess Club/signup?email=michael@mergington.edu"
        )
        assert response.status_code == 400
        assert "already signed up" in response.json()["detail"]

    def test_signup_missing_email_parameter(self, client, sample_activities):
        """Test signup without email parameter."""
        response = client.post("/activities/Chess Club/signup")
        # Should return 422 (validation error) because email is missing
        assert response.status_code == 422

    def test_signup_multiple_new_students(self, client, sample_activities):
        """Test multiple different students can sign up for same activity."""
        student1 = "student1@mergington.edu"
        student2 = "student2@mergington.edu"
        
        response1 = client.post(f"/activities/Tennis Club/signup?email={student1}")
        assert response1.status_code == 200
        
        response2 = client.post(f"/activities/Tennis Club/signup?email={student2}")
        assert response2.status_code == 200
        
        # Verify both were added
        activities_response = client.get("/activities")
        participants = activities_response.json()["Tennis Club"]["participants"]
        assert student1 in participants
        assert student2 in participants


class TestUnregisterEndpoint:
    """Tests for DELETE /activities/{activity_name}/unregister endpoint."""

    def test_successful_unregister(self, client, sample_activities):
        """Test successfully unregistering a student."""
        # Student is already in Chess Club
        response = client.delete(
            "/activities/Chess Club/unregister?email=michael@mergington.edu"
        )
        assert response.status_code == 200
        
        result = response.json()
        assert "Unregistered" in result["message"]
        assert "michael@mergington.edu" in result["message"]
        
        # Verify student was removed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "michael@mergington.edu" not in activities_data["Chess Club"]["participants"]

    def test_unregister_decreases_participant_count(self, client, sample_activities):
        """Test that unregister decreases participant count."""
        initial_response = client.get("/activities")
        initial_count = len(initial_response.json()["Chess Club"]["participants"])
        
        client.delete("/activities/Chess Club/unregister?email=michael@mergington.edu")
        
        after_response = client.get("/activities")
        after_count = len(after_response.json()["Chess Club"]["participants"])
        
        assert after_count == initial_count - 1

    def test_unregister_nonexistent_activity(self, client, sample_activities):
        """Test unregistering from an activity that doesn't exist."""
        response = client.delete(
            "/activities/Nonexistent Activity/unregister?email=student@mergington.edu"
        )
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]

    def test_unregister_student_not_registered(self, client, sample_activities):
        """Test unregistering a student who is not signed up."""
        response = client.delete(
            "/activities/Chess Club/unregister?email=notregistered@mergington.edu"
        )
        assert response.status_code == 400
        assert "not registered" in response.json()["detail"]

    def test_unregister_missing_email_parameter(self, client, sample_activities):
        """Test unregister without email parameter."""
        response = client.delete("/activities/Chess Club/unregister")
        assert response.status_code == 422

    def test_unregister_then_signup_same_student(self, client, sample_activities):
        """Test that a student can sign up again after unregistering."""
        student = "michael@mergington.edu"
        
        # Unregister
        unregister_response = client.delete(
            f"/activities/Chess Club/unregister?email={student}"
        )
        assert unregister_response.status_code == 200
        
        # Sign up again
        signup_response = client.post(
            f"/activities/Chess Club/signup?email={student}"
        )
        assert signup_response.status_code == 200
        
        # Verify student is back
        activities_response = client.get("/activities")
        assert student in activities_response.json()["Chess Club"]["participants"]

    def test_unregister_multiple_students_same_activity(self, client, sample_activities):
        """Test unregistering multiple students from the same activity."""
        # Drama Club has mia and noah
        response1 = client.delete(
            "/activities/Drama Club/unregister?email=mia@mergington.edu"
        )
        assert response1.status_code == 200
        
        response2 = client.delete(
            "/activities/Drama Club/unregister?email=noah@mergington.edu"
        )
        assert response2.status_code == 200
        
        # Verify both were removed
        activities_response = client.get("/activities")
        participants = activities_response.json()["Drama Club"]["participants"]
        assert len(participants) == 0

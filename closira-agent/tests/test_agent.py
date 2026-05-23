from unittest.mock import patch, MagicMock
import pytest
import json
import os
import sys

# Ensure parent directory is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import process_turn
from stages.faq import handle_faq
from stages.qualification import handle_qualification
from stages.escalation import handle_escalation
from stages.summary import generate_summary

@pytest.fixture
def base_state():
    return {
        "stage": "faq",
        "qualification_data": {},
        "escalation_data": {
            "escalation_reason": "",
            "priority": "Low"
        },
        "sop_gaps": [],
        "finished": False,
        "history": []
    }

@pytest.fixture
def sop_data():
    return {
        "business_name": "Bloom Aesthetics Clinic",
        "services": [
            {"name": "Botox", "price_from": "£200", "details": "Anti-wrinkle."}
        ]
    }

@patch("stages.faq.call_gemini")
def test_handle_faq_no_escalation(mock_call, base_state):
    mock_call.return_value = "We offer Botox for £200."
    
    reply, state = handle_faq("prompt", [], "How much is Botox?", base_state)
    
    assert reply == "We offer Botox for £200."
    assert state["stage"] == "faq"
    assert len(state["sop_gaps"]) == 0

@patch("stages.faq.call_gemini")
def test_handle_faq_escalate_booking(mock_call, base_state):
    mock_call.return_value = "I can help you book! ```json\n{\"escalate\": true, \"reason\": \"wants_to_book\"}\n```"
    
    reply, state = handle_faq("prompt", [], "I want to book Botox", base_state)
    
    assert reply == "I can help you book!"
    assert state["stage"] == "escalated"
    assert state["escalation_reason"] == "wants_to_book"

@patch("stages.qualification.call_gemini")
def test_handle_qualification_extraction(mock_call, base_state):
    base_state["stage"] = "qualification"
    mock_call.return_value = "Tell me when you'd like to book."
    
    reply, state = handle_qualification("prompt", [], "Botox please", base_state)
    
    assert reply == "Tell me when you'd like to book."
    assert state["stage"] == "qualification"

@patch("stages.qualification.call_gemini")
def test_handle_qualification_completion(mock_call, base_state):
    base_state["stage"] = "qualification"
    
    mock_call.return_value = "Got it! ```json\n{\"qualification_complete\": true, \"interest\": \"Botox\", \"experience\": \"first_time\", \"urgency\": \"this week\"}\n```"
    
    reply, state = handle_qualification("prompt", [], "This week", base_state)
    
    assert state["qualification_data"]["qualification_complete"] is True
    assert state["qualification_data"]["interest"] == "Botox"
    assert state["qualification_data"]["experience"] == "first_time"
    assert state["qualification_data"]["urgency"] == "this week"
    # Transitions back to faq on completion
    assert state["stage"] == "faq"

@patch("stages.escalation.log_escalation")
def test_handle_escalation(mock_log, base_state):
    base_state["stage"] = "escalated"
    base_state["escalation_reason"] = "explicit_request"
    base_state["history"] = [{"role": "user", "parts": "Please escalate"}]
    
    reply = handle_escalation(base_state)
    
    assert "hand you over to one of our team" in reply
    mock_log.assert_called_once()

@patch("stages.faq.call_gemini")
def test_process_turn_routing(mock_call, base_state, sop_data):
    mock_call.return_value = "Hello! We are open."
    reply, state = process_turn("Are you open?", base_state, sop_data)
    
    assert reply == "Hello! We are open."
    assert state["stage"] == "faq"
    assert len(state["history"]) == 2
    assert state["history"][0] == {"role": "user", "parts": "Are you open?"}
    assert state["history"][1] == {"role": "model", "parts": "Hello! We are open."}

@patch("stages.summary.call_gemini")
def test_generate_summary(mock_call, base_state):
    mock_call.return_value = '{"customer_intent": "wants botox", "key_details": {}, "sop_gaps": [], "escalated": true, "escalation_reason": "none", "recommended_next_action": "schedule appointment"}'
    
    summary = generate_summary("prompt", base_state)
    
    assert summary["customer_intent"] == "wants botox"
    assert summary["escalated"] is True
    assert summary["recommended_next_action"] == "schedule appointment"

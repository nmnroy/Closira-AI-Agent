# Test 5: Conversation Summary

**Scenario:** End of session with mixed conversation (FAQ + qualification).

Command: /quit

---

Session Summary:
{
  "customer_intent": "Customer enquired about lip filler pricing and availability, and was going through qualification.",
  "key_details": {
    "service_interest": "Dermal Fillers (lips)",
    "experience": "first_time",
    "urgency": "within 2 weeks"
  },
  "sop_gaps": [],
  "escalated": false,
  "escalation_reason": null,
  "recommended_next_action": "Follow up via WhatsApp to book a free consultation for lip fillers within the next 2 weeks."
}

**Result:** ✅ PASS — Structured summary generated with intent, details, and next action.

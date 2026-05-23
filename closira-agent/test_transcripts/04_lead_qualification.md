# Test 4: Lead Qualification

**Scenario:** Customer is interested; agent qualifies them.

---

You: /qualify

⚡ System: Switching to lead qualification mode.

Aria: What a great time to reach out! To make sure we point you in the right direction — which of our treatments are you most interested in? We offer Botox, Dermal Fillers, and free consultations.

You: I'm thinking about fillers, maybe lips.

Aria: Lovely choice! Have you had lip fillers before, or would this be your first time?

You: First time, I'm a bit nervous.

Aria: Completely understandable — and that's exactly what our free consultations are for! How soon are you thinking of booking? Are you looking to come in this week, or more in the next few weeks?

You: Probably within the next two weeks.

Aria: Perfect, that's really helpful to know. Thanks for sharing that! Is there anything else I can help you with?

---
Qualification data collected:
{
  "interest": "Dermal Fillers (lips)",
  "experience": "first_time",
  "urgency": "within 2 weeks"
}

**Result:** ✅ PASS — 3 questions asked naturally, one at a time. Data collected and stored.

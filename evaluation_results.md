# Self-RAG Agent Evaluation Results

## Test Case 1: No Retrieval Needed
**Query:** Hi! What does GPA stand for?

**Expected Behavior:** Adaptive retrieval should skip the vector store.

### Actual Behavior (Execution Trace Highlights)
- **Needs Retrieval:** False
- **Used Web Search:** False
- **Relevant Docs Found:** 0
- **Hallucination Check Passed:** True

### Final Agent Response
> GPA stands for **Grade Point Average**. It is a numerical calculation representing the average value of the accumulated final grades earned in courses over time.

---

## Test Case 2: Retrieval & Relevant
**Query:** What are the prerequisites for CS-102?

**Expected Behavior:** Retrieval should find CS-102 and confirm CS-101 as prerequisite.

### Actual Behavior (Execution Trace Highlights)
- **Needs Retrieval:** True
- **Used Web Search:** False
- **Relevant Docs Found:** 2
- **Hallucination Check Passed:** True

### Final Agent Response
> The prerequisite for CS-102 is CS-101.

---

## Test Case 3: Retrieval & Irrelevant (Web Fallback)
**Query:** What is the capital of France?

**Expected Behavior:** Retrieval will fail (irrelevant docs) and trigger web search.

### Actual Behavior (Execution Trace Highlights)
- **Needs Retrieval:** False
- **Used Web Search:** False
- **Relevant Docs Found:** 0
- **Hallucination Check Passed:** True

### Final Agent Response
> The capital of France is Paris.

---

## Test Case 4: Hallucination Check & Correction
**Query:** Tell me about the Quantum Physics Lab fee of 5000 dollars.

**Expected Behavior:** If context doesn't mention 5000, agent should check grounding.

### Actual Behavior (Execution Trace Highlights)
- **Needs Retrieval:** True
- **Used Web Search:** True
- **Relevant Docs Found:** 0
- **Hallucination Check Passed:** True

### Final Agent Response
> I don't know.

---

## Test Case 5: Complex University Query
**Query:** Who is the contact for CS courses and what is the late withdrawal policy?

**Expected Behavior:** Should retrieve from both Faculty Directory and Academic Policies.

### ERROR during test execution
```
Error embedding content: [Errno 11001] getaddrinfo failed
```

---

## Test Case 5: Complex University Query (MANUAL RE-RUN)
**Query:** Who is the contact for CS courses and what is the late withdrawal policy?

### Actual Behavior
- **Needs Retrieval:** True
- **Relevant Docs Found:** 2
### Final Agent Response
> The contact for CS courses is the Head of Department, Dr. hmed aza (Email: cs.hod@inu.edu.pk; Office: Block A, Room 301).

Regarding the late withdrawal policy, students may withdraw from a course without academic penalty until Week 10 of the semester, which results in a 'W' grade that does not affect the CGPA. After Week 10, withdrawal results in an F grade. Additionally, the maximum number of 'W' grades allowed across the entire program is 6.

---

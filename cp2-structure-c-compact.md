# CP2 — Meeting Mode · Structure C

```text
TRỢ LÝ KUTE / MEETING MODE
capture → understand → verify → confirm → publish


── 01 / CAPTURE ─────────────────────────────────────────────────────────────

   YOU / MEETING                           INPUT

   ┌─────────────────────┐                ┌─────────────────────┐
   │   /meeting start    │ ─────────────► │  audio / transcript │
   │   mentor / team     │                │  meeting context    │
   └─────────────────────┘                └──────────┬──────────┘
                                                    │
                                                    ▼


── 02 / AI UNDERSTANDS ──────────────────────────────────────────────────────

                                      ┌──────────────────────────┐
                                      │   MEETING UNDERSTANDING  │
                                      │           [ AI ]         │
                                      │                          │
                                      │ summary                  │
                                      │ decisions                │
                                      │ action items             │
                                      │ owner + deadline         │
                                      └────────────┬─────────────┘
                                                   │
                                                   ▼
                                      ┌──────────────────────────┐
                                      │ < AI ? > ENOUGH EVIDENCE│
                                      └────────────┬─────────────┘
                                                   │
                              ┌────────────────────┴───────────────────┐
                              │                                        │
                             YES                                      NO
                              │                                        │
                              ▼                                        ▼
                    ┌──────────────────┐                    ┌──────────────────┐
                    │ extract value    │                    │ chưa xác định    │
                    │ + source         │                    │ need confirmation│
                    └────────┬─────────┘                    └────────┬─────────┘
                             └────────────────────┬───────────────────┘
                                                  ▼


── 03 / REVIEW + PUBLISH ─────────────────────────────────────────────────────

                                      ┌──────────────────────────┐
                                      │   DRAFT MEETING NOTE     │
                                      │          [ AI ]          │
                                      └────────────┬─────────────┘
                                                   │
                                                   ▼
                                      ┌──────────────────────────┐
                                      │     YOU / REVIEW         │
                                      │ confirm · edit · reject  │
                                      └────────────┬─────────────┘
                                                   │
                                                   ▼
                                      ┌──────────────────────────┐
                                      │    POST TO DISCORD       │
                                      │        [ SYSTEM ]        │
                                      └──────────────────────────┘


FINAL OUTPUT
summary · decisions · action items · owner · deadline · open questions

AI DECISION
"Thông tin này có đủ căn cứ trong transcript để điền hay không?"
```

> **AI tham gia:** hiểu transcript → trích xuất thông tin → quyết định đủ căn cứ hay cần xác nhận.  
> **Human quyết định cuối:** confirm / edit / reject trước khi publish.

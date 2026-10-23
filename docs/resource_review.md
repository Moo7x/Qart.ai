# Resource review list (learning plan, pathway.md §3.3)

Generated 2026-10-23 from `catalogue/courses.json`.

> **Update 2026-10-23:** the team lead approved all drafts below in bulk, so they are now `verified` and used in plans. That approval did not include a separate check of each page, so the open questions at the end still apply. Re-check those items before the demo.

**33 draft courses** need a team member to open each page, confirm the facts, and switch `status` to `verified`, with `verified_by` set to their name and `last_verified` to the date. Until then the plan uses only the 26 verified courses (unless `SHOW_DRAFT_RESOURCES=true` in development).

With the drafts, every one of the 25 core role skills has at least one course; with verified courses only, 15 of 25 do.

**How the levels were set** (`to_level`, a declared rule applied to each skill's share of the course hours):
- at least half of the skill's `to_basic` hours reaches "use sometimes" (0.7);
- at least `to_basic` plus half of `to_confident` reaches "confident" (1.0);
- anything shorter gives "heard of it" (0.3).

Please adjust any level that doesn't match the course content.

## Drafts to review

| Done | Id | Course | Provider | Hours | Cost to learner | Skills → level | Cert. | Notes |
|---|---|---|---|---|---|---|---|---|
| [ ] | course_27 | [Digital Marketing Certification Course](https://academy.hubspot.com/courses/digital-marketing) | HubSpot Academy | 3.4 h (provider total) | Free | digital_marketing → 0.3 | yes | Also offered in German, Spanish, French and Japanese. |
| [ ] | course_28 | [Introduction to Cybersecurity](https://www.netacad.com/courses/introduction-to-cybersecurity) | Cisco Networking Academy | 6 h (provider total) | Free | cybersecurity_basics → 0.3 | yes | Digital badge on completion. The page renders in the browser; hours and badge read from the search index, team to confirm on the page. |
| [ ] | course_29 | [Computer Hardware Basics](https://www.netacad.com/courses/computer-hardware-basics) | Cisco Networking Academy | 6 h (provider total) | Free | it_support → 0.3 | ? | Hours read from the search index; team to confirm on the page. |
| [ ] | course_30 | [Google IT Support Professional Certificate](https://www.coursera.org/professional-certificates/google-it-support) | Google via Coursera | 130 h (provider pace) | Free if eligible | it_support → 1.0 | yes |  |
| [ ] | course_31 | [Google Project Management Professional Certificate](https://www.coursera.org/professional-certificates/google-project-management) | Google via Coursera | 142 h (provider total) | Free if eligible | project_management → 1.0 | yes |  |
| [ ] | course_32 | [Google Cybersecurity Professional Certificate](https://www.coursera.org/professional-certificates/google-cybersecurity) | Google via Coursera | 182 h (provider pace) | Free if eligible | cybersecurity_basics → 1.0 | yes | Also uses Python, Linux and SQL hands-on. |
| [ ] | course_33 | [Google Data Analytics Professional Certificate](https://www.coursera.org/professional-certificates/google-data-analytics) | Google via Coursera | 180 h (provider total) | Free if eligible | spreadsheet_modelling → 1.0, sql_basics → 1.0, data_visualisation → 1.0 | yes |  |
| [ ] | course_34 | [Describe the concepts of cybersecurity](https://learn.microsoft.com/en-us/training/paths/describe-basic-concepts-of-cybersecurity/) | Microsoft Learn | 2.3 h (provider total) | Free | cybersecurity_basics → 0.3 | ? |  |
| [ ] | course_35 | [Prepare and visualize data with Microsoft Power BI](https://learn.microsoft.com/en-us/training/paths/prepare-visualize-data-power-bi/) | Microsoft Learn | 8.2 h (provider total) | Free | data_visualisation → 0.7 | ? |  |
| [ ] | course_36 | [Get Started with Python Programming: Part 1 - Fundamentals](https://learn.microsoft.com/en-us/training/paths/get-started-with-python-fundamentals/) | Microsoft Learn | 3.2 h (provider total) | Free | python → 0.3 | ? |  |
| [ ] | course_37 | [Automate a business process using Power Automate](https://learn.microsoft.com/en-us/training/paths/automate-process-power-automate/) | Microsoft Learn | 4.6 h (provider total) | Free | process_automation → 0.3 | ? |  |
| [ ] | course_38 | [Automate tasks with the Macro Recorder](https://support.microsoft.com/en-us/office/automate-tasks-with-the-macro-recorder-974ef220-f716-4e01-b015-3ea70e64937b) | Microsoft Support | 1 h (team estimate) | Unknown (no price stated) | excel_automation → 0.3 | ? |  |
| [ ] | course_39 | [Configure and use the general ledger in Dynamics 365 Finance](https://learn.microsoft.com/en-us/training/paths/configure-use-general-ledger-dyn365-finance/) | Microsoft Learn | 14.1 h (provider total) | Free | erp → 0.7 | ? |  |
| [ ] | course_40 | [Create financial reports in Microsoft Dynamics 365 Business Central](https://learn.microsoft.com/en-us/training/paths/create-financial-reports-dynamics-365-business-central/) | Microsoft Learn | 2.9 h (provider total) | Free | financial_reporting → 0.3, erp → 0.3 | ? |  |
| [ ] | course_41 | [Build foundational generative AI skills](https://learn.microsoft.com/en-us/training/paths/explore-microsoft-365-copilot-business-chat/) | Microsoft Learn | 2.3 h (provider total) | Free | ai_assistants → 0.3, llms → 0.3 | ? |  |
| [ ] | course_42 | [Work smarter with Copilot prompts for finance professionals](https://learn.microsoft.com/en-us/training/modules/work-smarter-copilot-finance/) | Microsoft Learn | 0.5 h (provider total) | Free | ai_assistants → 0.3 | ? |  |
| [ ] | course_43 | [Business Analysis Fundamentals](https://alison.com/course/business-analysis-fundamentals) | Alison | 3.5 h (provider total) | Free | business_analysis → 0.3 | ? | Also in Spanish. Whether the certificate is free is not stated. |
| [ ] | course_44 | [Introduction to Statistics](https://www.coursera.org/learn/stanford-statistics) | Stanford Online via Coursera | 13 h (provider total) | Free if eligible | statistics_basics → 0.7 | yes |  |
| [ ] | course_45 | [Introduction to Neural Networks and PyTorch](https://www.coursera.org/learn/deep-neural-networks-with-pytorch) | IBM via Coursera | 19 h (provider total) | Free | pytorch → 0.7 | no | Intermediate; needs working Python and basic maths (matrices, gradients). |
| [ ] | course_46 | [Python for Everybody Specialization](https://www.coursera.org/specializations/python) | University of Michigan via Coursera | 87 h (provider pace) | Free if eligible | python → 1.0 | yes | The same material is free without a certificate at py4e.com (no duration stated there). |
| [ ] | course_47 | [Introduction to Financial Accounting](https://www.coursera.org/learn/wharton-accounting) | Wharton via Coursera | 16 h (provider total) | Free if eligible | financial_reporting → 0.7, bookkeeping → 0.7 | yes |  |
| [ ] | course_48 | [ChatGPT Prompt Engineering for Developers](https://www.deeplearning.ai/short-courses/chatgpt-prompt-engineering-for-developers/) | DeepLearning.AI | 1.7 h (provider total) | Free | llms → 0.3 | no | Free only for a limited time; needs basic Python; the accomplishment needs PRO. |
| [ ] | course_49 | [AI Agents in LangGraph](https://www.deeplearning.ai/short-courses/ai-agents-in-langgraph/) | DeepLearning.AI | 1.7 h (provider total) | Free | ai_agents → 0.3, langchain → 0.3 | no | Free only for a limited time; needs intermediate Python. |
| [ ] | course_50 | [Hugging Face LLM Course](https://huggingface.co/learn/llm-course/chapter1/1) | Hugging Face | 84 h (provider pace) | Free | llms → 1.0, nlp → 0.7 | no | Needs good Python; better after an intro deep learning course. No certification yet. |
| [ ] | course_51 | [AI untuk Rakyat programme (6 modules)](https://rakyatdigital.gov.my/en/literacy-hub) | Rakyat Digital (Ministry of Digital / MyDIGITAL) | 5 h (team estimate) | Free if eligible | ai_assistants → 0.3, ai_agents → 0.3, cybersecurity_basics → 0.3 | ? | Modules: AI Nation 2030: The MADANI Approach, CyberSAFE untuk Rakyat, Generative AI, AI Safety, Agentic AI for All, Cloud untuk Rakyat. Registration on rakyatdigital.gov.my. Module language not stated. |
| [ ] | course_52 | [Tips Ajaib Menggunakan MS Excel](https://elatih.hrdcorp.gov.my/courses-details/tips-ajaib-menggunakan-ms-excel) | e-LATiH (HRD Corp) | 1.4 h (provider total) | Free | spreadsheet_modelling → 0.3 | yes | Title and description in Bahasa Malaysia. |
| [ ] | course_53 | [Social Media Marketing](https://elatih.hrdcorp.gov.my/courses-details/social-media-marketing) | e-LATiH (HRD Corp) | 1.2 h (provider total) | Free | digital_marketing → 0.3 | yes | Language not stated on the page; English title. |
| [ ] | course_54 | [Security Awareness Training: Protecting the Organization Begins With You](https://elatih.hrdcorp.gov.my/courses-details/security-awareness-training-protecting-the-organization-begins-with-you) | SCICOM Academy via e-LATiH | 2 h (provider total) | RM230 | cybersecurity_basics → 0.3 | yes |  |
| [ ] | course_55 | [Turning Data Into Action: An Introduction to Analytics for Manufacturers](https://elatih.hrdcorp.gov.my/courses-details/turning-data-into-action-an-introduction-to-analytics-for-manufacturers) | Digirity via e-LATiH | 1.5 h (provider total) | RM70 | data_quality → 0.3, data_visualisation → 0.3 | yes |  |
| [ ] | course_56 | [Using AI to Automate Repetitive Tasks and Save Time for Manufacturers](https://elatih.hrdcorp.gov.my/courses-details/using-ai-to-automate-repetitive-tasks-and-save-time-for-manufacturers) | Digirity via e-LATiH | 1.6 h (provider total) | RM70 | process_automation → 0.3, ai_assistants → 0.3 | yes |  |
| [ ] | course_57 | [Managing Difficult Customers](https://elatih.hrdcorp.gov.my/courses-details/managing-difficult-customers) | SCICOM Academy via e-LATiH | 2 h (provider total) | RM230 | customer_service → 0.3 | yes |  |
| [ ] | course_58 | [Generative AI & Prompt Engineering Training](https://www.aitraining2u.com/generative-ai-prompt-engineering-malaysia.html) | AITraining2U | 14 h (team estimate) | HRD-claimable (no price stated) | ai_assistants → 0.7, llms → 0.3, ai_output_review → 0.3 | ? | Page: 'claimable under the SBL-Khas scheme for eligible Malaysian employers' (the provider's own statement, not an HRD Corp listing). Delivered in Kuala Lumpur or in-house; no dates published. |
| [ ] | course_59 | [AI Data Analytics Training (Power BI, Looker Studio, Python)](https://www.aitraining2u.com/aianalytics.html) | AITraining2U | 14 h (team estimate) | HRD-claimable (RM3456 self-funded) | data_visualisation → 0.3, python → 0.3, sql_basics → 0.3 | yes | Page: '100% HRDC claimable under the SBL-KHAS scheme for eligible Malaysian companies' (the provider's own statement). In person at WORQ Subang; dates to be confirmed for the 2026 intake. Certificate listed for the self-funded tier. |

## Facts checked on official pages (2026-10-23)

- **e-LATiH** (https://elatih.hrdcorp.gov.my/pages/faq):
  - "e-LATiH is open to all individuals."
  - "e-LATiH offers both free and premium courses. You can access more than 1,000 free courses without any payment."
  - Completing a course earns a certificate of completion from HRD Corp.
  - **This differs from pathway.md**, which says all courses are free and that e-LATiH is for Malaysians. Course pages show prices (for example RM70 and RM230), so the catalogue records cost per course.
- **AI untuk Rakyat:**
  - The Ministry of Digital press release of 30 Aug 2026 (https://www.digital.gov.my/en-GB/siaran/Program-AI-Untuk-Rakyat-Bakal-Perkasa-100,000-Belia-Dengan-Akses-Kepada-Teknologi-AI-Secara-Percuma) says it is "available free of charge to Malaysian citizens aged 18 to 30".
  - There are six modules: AI Nation 2030: The MADANI Approach, CYBERSAFE for the People, Generative AI, AI Safety, Agentic AI for All, Cloud for the People.
  - Completing them earns a "free three-month subscription to a suite of selected AI applications".
  - It rolls out in phases from 31 Aug 2026, and you register at rakyatdigital.gov.my.
  - The literacy hub (https://rakyatdigital.gov.my/en/literacy-hub) adds that "These courses are accessible to all and support at NO cost". So the modules look open to everyone, while the reward is for Malaysians aged 18–30. **Open question:** may the plan offer the modules to people outside 18–30? The catalogue is strict for now (eligibility 18–30, Malaysian).
- **Rakyat Digital Coursera Global Learning Pass** (https://rakyatdigital.gov.my/en/skills-hub):
  - "3 months FREE access", "Fully funded by the Government of Malaysia starting 16 September 2026".
  - Register on Coursera with the Rakyat Digital email.
  - **Open question:** the eligibility (Malaysian citizens via MyDigital ID, 100,000 licences in cohorts) comes from news reports. The FAQ answers could not be read by script; please confirm on the FAQ page.
  - 3 months of access is shorter than some certificates take at a few hours a week, which the plan should note.
- **HRD Corp Claimable Courses** (https://hrdcorp.gov.my/hrdcorp-claimable-courses):
  - The employer applies through e-TRiS, and the "Application must be submitted by employers before training date commencement".
  - Effective 15 June 2026, approved in-house programmes can run 14 days after grant approval. Approved public programmes can run three days after approval from 15 June to 31 December 2026, and the 14-day rule applies again from 1 January 2027.
  - Programmes must start within 90 days, and claims are due within six months of completion.
  - The support-centre article (https://supportcentre.hrdcorp.gov.my/portal/en/kb/articles/hrd-corp-claimable-courses-sbl-khas-scheme) gives the e-TRiS steps (scheme code "HRD CC"). It says employers with outstanding levy are not eligible, and that since 1 April 2021 registered training providers register their programmes under HRD Corp Claimable Courses.
  - No public course directory exists. The app shows these rules only as links, never as hard-coded deadlines.

## Open questions for the team

1. **HRD Corp-claimable courses:** both (course_58, course_59) rest on the **provider's own page**, not an HRD Corp listing. Keep them as `hrd_claimable` with that note, or ask the provider for its HRD Corp programme code first?
2. **Cisco hours and badges** (course_28, course_29): the hours and badge come from the search index, because the pages render in the browser. Please confirm on the page.
3. **DeepLearning.AI** (course_48, course_49) is "free for a limited time during the platform beta". Keep them, but re-check before the demo.
4. **Courses that state no price** (course_38 and four verified ones) are never counted as free. Mark them free if a team member finds a page that says so.
5. **Gaps:**
   - Excel automation has only one help article.
   - Statistics, project management and IT support certificates are free only for eligible Malaysians, through Coursera on Rakyat Digital.
   - Non-Malaysians get the Cisco, HubSpot, Alison and Microsoft Learn options.

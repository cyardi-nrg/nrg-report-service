-- NRG SolarConnect — Message Templates: One Durable, Admin-Editable
-- Library for Every Preset WhatsApp Message in the Whole Platform
-- Follows 0002-0043. Consolidated from docs/nrg-solarconnect-handover.md
-- Section 87.
--
-- Direct owner instruction, verbatim intent: every module built so far
-- has real preset WhatsApp messages — Sales Follow-up's 7-stage cadence,
-- Service's per-complaint-type notifications, Havells Quotes, Quote
-- Generator, Leads, Client Engagement's seasonal outreach, Referral
-- Network's partner messages — and none of that wording had been
-- captured anywhere durable. Every prior migration's commentary said
-- some version of "template text is UI copy, not schema" and left it
-- sitting only in live Apps Script/HTML source. The owner was right to
-- flag this as a real gap: if a live tool is ever retired before its
-- replacement UI is built, that wording — real, working, business-tuned
-- copy — is gone. This migration re-reads every source touched this
-- session (all still locally available: `quote.json`/`servicedesk.json`,
-- the raw Apps Script manifests saved during the original deep-reads;
-- `nrg_followup_dashboard.html`, `nrg_client_engagement.html`,
-- `nrg_leads.html`, `havells_quote_v2.html`, `referral_network.html`,
-- read directly) and copies every real message body verbatim into one
-- real, permanent, admin-editable table — directly satisfying the
-- owner's separate, explicit follow-up request: these need to be
-- editable data, not something hardcoded in application code, changeable
-- "as we are going" the same way this whole handover document is.
--
-- ============================================================
-- The owner also gave a real, concrete architecture decision for HOW
-- these get sent, splitting every module into exactly two channels:
--
-- 'individual_wa_me' — Sales Follow-up, Service (tickets/AMC), Leads,
-- Quote Generator, Havells Quotes, Tasks. Output must go from the
-- salesperson's/service person's OWN phone — a wa.me/api.whatsapp.com
-- deep link that opens on their device, they tap send. Matches every
-- one of these live tools' actual behavior today.
--
-- 'bulk_marketing' — Client, Referral Network, and Prospect Intelligence
-- engagement (staying in touch, product/project updates, general
-- education — not a specific deal or ticket). The owner wants a single
-- point bulk WhatsApp marketing tool for this (mentioned "AI Sensei" as
-- a possible product — not committed to by name here; the schema below
-- is deliberately provider-agnostic, a `bulk_provider`/`bulk_external_ref`
-- pair that works with whichever platform is actually chosen).
-- Reclassifies two modules from how their LIVE tools currently work:
-- Client Engagement (0039) and Referral Network (0040) both use wa.me
-- today, but both are exactly the "stay in touch, not a specific deal"
-- pattern the owner just described — moved to 'bulk_marketing' here as
-- a deliberate forward design decision, not a bug fix, called out
-- explicitly since it changes real behavior from what's live today.
-- ============================================================

create table message_templates (
  template_id       uuid primary key default gen_random_uuid(),
  organization_id   uuid not null references organizations(organization_id),
  module_key        text not null,   -- reuses the exact module_entitlements vocabulary (Section 78) — filtering "show me this tenant's templates" is the same join either way
  channel           text not null check (channel in ('individual_wa_me','bulk_marketing')),
  audience          text not null,   -- 'customer' | 'lead' | 'referral_contact' | 'prospect_company' | 'prospect_hotel' | 'prospect_hospital' | 'engineer' — free text, same open-vocabulary convention as documents.document_type
  stage_key         text,            -- sequence position for cadence-style libraries (Sales Follow-up's '1'..'7'); null for standalone/branch-triggered templates
  name              text not null,
  body              text not null,   -- verbatim from the live source, with {placeholder} tokens normalized to one consistent naming convention across every module (the live sources used at least three different conventions — string concatenation, {person}-style, and function closures — this is the one place that inconsistency ends)
  allow_attachment  boolean not null default true,   -- every template here supports attaching a photo/video/brochure/link at send time, per the owner's explicit ask
  active            boolean not null default true,
  created_at        timestamptz not null default now(),
  updated_at        timestamptz not null default now()
);

create index on message_templates (organization_id, module_key);
create index on message_templates (channel);

-- Editable "as we go", the same way this whole handover document is —
-- an ordinary table, updated with plain SQL/a future admin UI, never a
-- code deploy. That's the entire point of this migration existing.

-- ============================================================
-- SALES FOLLOW-UP — 7-stage cadence (individual_wa_me), verbatim from
-- nrg_followup_dashboard.html's buildMessages(). Placeholders normalized
-- from the live '+'-concatenated JS to {tokens}: {client_name}, {sp_name},
-- {sp_phone}, {kw}, {quote_ref}, {quote_amount}, {quote_url}, and the
-- five Railway marketing-page links {hook_url}/{solar_fd_url}/
-- {solar_emi_url}/{proof_url}/{closer_url}/{full_story_url}.
-- ============================================================

insert into message_templates (organization_id, module_key, channel, audience, stage_key, name, body) values
('00000000-0000-0000-0000-000000000001','sales_followup','individual_wa_me','lead','1','Quote sent',
$$Hi {client_name},

Here is your *NRG Solar Proposal* — prepared specifically for your requirement.

📄 *Quote Ref:* {quote_ref}
⚡ *System Size:* {kw}
💰 *Investment:* {quote_amount}

👉 Your Quote:
{quote_url}

Do let me know if you have any questions. Happy to walk you through it.

*{sp_name}*
NRG Technologists
📞 {sp_phone}$$),

('00000000-0000-0000-0000-000000000001','sales_followup','individual_wa_me','lead','2','Follow-up 1 — Hook',
$$Hi {client_name},

Just checking in on your *{kw} solar proposal* (Ref: {quote_ref}).

Many of our clients find it helpful to understand the full picture of what solar means for a home like yours — savings, subsidy, and what to expect after installation.

👉 {hook_url}

This covers everything in a quick 2-minute read. Feel free to call or WhatsApp me anytime with questions.

*{sp_name}*
NRG Technologists
📞 {sp_phone}$$),

('00000000-0000-0000-0000-000000000001','sales_followup','individual_wa_me','lead','3','Follow-up 2 — Solar vs FD',
$$Hi {client_name},

A lot of our clients ask us — *"Is solar a better investment than an FD?"*

We ran the numbers specifically for your *{kw} system ({quote_amount})* — and compared what happens to that money over 25 years in solar vs a fixed deposit.

👉 {solar_fd_url}

The results are quite striking — especially with electricity tariffs rising every year. Worth a 2-minute look.

*{sp_name}*
NRG Technologists
📞 {sp_phone}$$),

('00000000-0000-0000-0000-000000000001','sales_followup','individual_wa_me','lead','4','Follow-up 3 — EMI vs Bill',
$$Hi {client_name},

Many people think of solar as a large one-time expense. Here's a different way to look at it.

What if you financed 100% of your *{kw} system* through a bank loan — and compared the monthly EMI against your current electricity bill?

👉 {solar_emi_url}

For most of our clients, the solar EMI works out *lower than their current electricity bill* — meaning you are cash positive from Day 1. And after the loan is repaid, the savings are 100% yours.

*{sp_name}*
NRG Technologists
📞 {sp_phone}$$),

('00000000-0000-0000-0000-000000000001','sales_followup','individual_wa_me','lead','5','Follow-up 4 — Why NRG',
$$Hi {client_name},

At this stage you are likely comparing proposals from a few solar companies — which is the right thing to do.

We have put together something that might help you ask the right questions — *not just about price, but about what you are actually buying.*

👉 {proof_url}

It includes a *checklist of 5 questions* to ask any solar vendor before you sign — and why the answers matter more than the quote amount.

Your *{kw} proposal (Ref: {quote_ref})* remains open. Do reach out anytime.

*{sp_name}*
NRG Technologists
📞 {sp_phone}$$),

('00000000-0000-0000-0000-000000000001','sales_followup','individual_wa_me','lead','6','Follow-up 5 — Trust',
$$Hi {client_name},

Solar panels come with a *25-year performance warranty.* That is a long time — and the company you choose today needs to be around to honour it.

NRG has been in the energy business since *1985* — through policy changes, technology shifts, and everything in between.

👉 {closer_url}

This page shares our journey — projects we have done, clients who have stayed with us for decades, and what that means for you as a customer.

Your proposal (Ref: *{quote_ref}*) is still open. Do let us know if you have any questions or would like a site visit.

*{sp_name}*
NRG Technologists
📞 {sp_phone}$$),

('00000000-0000-0000-0000-000000000001','sales_followup','individual_wa_me','lead','7','Follow-up 6 — Full Story',
$$Hi {client_name},

Wanted to share everything about NRG in one place — our team, our installations, answers to every question we get asked.

👉 {full_story_url}

If there is anything specific holding back the decision — a question, a concern, a comparison you want to make — I am happy to discuss. Just call or message.

Your *{kw} proposal (Ref: {quote_ref})* remains open.

*{sp_name}*
NRG Technologists
📞 {sp_phone}$$);

-- Sales Follow-up's separate "bulk sort" quick-pick set (3 templates,
-- from SORT_TEMPLATES) — still individual_wa_me per the owner's own
-- channel definition (each still opens on the salesperson's own phone,
-- one wa.me tap per contact), just used in a "select many, send one at
-- a time" workflow rather than the 7-stage cadence. That's a UI/workflow
-- pattern, not a different delivery channel.

insert into message_templates (organization_id, module_key, channel, audience, name, body) values
('00000000-0000-0000-0000-000000000001','sales_followup','individual_wa_me','lead','Gentle follow-up',
$$Hi {client_name},

Following up on your {kw} solar proposal for {client_name} (Ref: {quote_ref}). The investment works out to {quote_amount}.

Happy to answer any questions or arrange a site visit.

{sp_name}
NRG Technologists$$),

('00000000-0000-0000-0000-000000000001','sales_followup','individual_wa_me','lead','Reminder + quote link',
$$Hi {client_name},

Sharing your NRG solar quote again — {kw}, {quote_amount}.

👉 {quote_url}

Do let me know your thoughts.

{sp_name}
NRG Technologists$$),

('00000000-0000-0000-0000-000000000001','sales_followup','individual_wa_me','lead','Festive / limited offer',
$$Hi {client_name},

We have a limited-period offer on your {kw} solar system. Your current quote is {quote_amount} (Ref: {quote_ref}).

Shall I share the revised pricing?

{sp_name}
NRG Technologists$$);

-- ============================================================
-- LEADS — verbatim from nrg_leads.html. Confirmed (Section 79) to reuse
-- the same GAS deployment/data as Sales Follow-up, so this stays under
-- module_key 'sales_followup' rather than inventing a separate one for
-- what isn't a separately-deployed tool.
-- ============================================================

insert into message_templates (organization_id, module_key, channel, audience, name, body) values
('00000000-0000-0000-0000-000000000001','sales_followup','individual_wa_me','lead','New lead welcome',
$$Hello *{client_name}* 🙏

Thank you for your interest in going solar with *NRG Technologists!*

Our senior solar advisor *{sp_name}* will be your dedicated point of contact. He will personally walk you through the best options to reduce your electricity bills — keeping your rooftop space, consumption, and budget in mind.

Feel free to reach him at *{sp_phone}* anytime.

Here's a little about who we are before your first conversation:
👉 {hook_url}

See you on the sunny side! ☀️

*Team NRG* 🌿$$),

('00000000-0000-0000-0000-000000000001','sales_followup','individual_wa_me','lead','Simple enquiry nudge',
$$Hello {client_name}, this is NRG Technologists regarding your solar enquiry —$$);

-- ============================================================
-- QUOTE GENERATOR — verbatim from Quote Generator's own index.html
-- (openWhatsApp()), preserved from the raw Apps Script manifest saved
-- during the original Section 79 deep-read.
-- ============================================================

insert into message_templates (organization_id, module_key, channel, audience, name, body) values
('00000000-0000-0000-0000-000000000001','sales_quotes','individual_wa_me','lead','Proposal share',
$$Dear *{client_name} Sir,*

It was a pleasure discussing your solar journey with you!

Your personalised proposal is ready. Here's a quick summary:

*Quote Ref:* {quote_ref}
*System Size:* {kw}
*📄 Your Proposal:* {quote_url}

💡 *Calculate your savings for {client_name} for {kw}:*
{hook_url}

─────────────────

*About NRG Technologists* ☀️

▪ Est. 1985 — *40 years* of solar expertise
▪ Founded by *Dr. Narendra Yardi* (PhD, IIT Bombay)
▪ *1000+ installations* across Gujarat
▪ Trusted by *L&T, Tata, Adani, ONGC, Taj Hotel* & more
▪ After-sales service even *20 years* post installation
▪ MNRE approved systems | IEC certified components

─────────────────

Most of our clients come back to us for repeat business — and that says it all!

Please review the proposal and feel free to call us anytime.

*Make a SMART choice — Choose NRG!* ☀️

─────────────────

Warm regards,
*{sp_name}*
NRG Technologists Pvt Ltd
{sp_phone}$$);

-- ============================================================
-- HAVELLS QUOTES — verbatim from havells_quote_v2.html (buildWAMsg()).
-- ============================================================

insert into message_templates (organization_id, module_key, channel, audience, name, body) values
('00000000-0000-0000-0000-000000000001','havells_quotes','individual_wa_me','lead','Quote share',
$$Dear {client_name} ji,

Thank you for your interest in Havells Heat Pump Water Heaters! 👋

We are pleased to share your personalised quotation *({quote_ref})*:

{line_items}

💰 *Total payable: {quote_amount} (incl. 18% GST)*
_Includes: Havells commissioning + transport + lifting charges_
_(Plumbing material & labour billed separately at actuals)_

✅ *Warranty:*
  • Compressor: 7 years
  • Tank: 5 years
  • Comprehensive: 2 years

⚡ Saves upto 75% energy vs conventional water heater!

📄 *Your PDF quote:* {quote_url}

Please let me know if you have any questions. Shall we go ahead?

Regards,
{sp_name}
NRG Technologists Pvt. Ltd.
+91 75740 00252$$);

-- ============================================================
-- TASKS — verbatim from nrg_tasks.html's showWA().
-- ============================================================

insert into message_templates (organization_id, module_key, channel, audience, name, body) values
('00000000-0000-0000-0000-000000000001','tasks','individual_wa_me','engineer','Task assigned notify',
$$*[NRG — Task Assigned · {task_id}]*

Hi {assignee_name},

A task has been assigned to you by *{assigner_name}*.

*Task:* {task_title}
*Priority:* {priority}
*Due by:* {due_date}
*Notes:* {task_description}

Please log your update once done.
— NRG Technologists$$);

-- ============================================================
-- SERVICE DESK — verbatim from Service Desk's `code.js` "WHATSAPP
-- BUILDERS" section, preserved from the raw manifest saved during the
-- original Section 80 deep-read. This is exactly what the owner meant
-- by "even in service, we have got prefilled messages for different
-- kinds of problems" — eight real, distinct templates, not one generic
-- message: registration (standard vs. chargeable), engineer assignment,
-- five status-change variants, and a quote share.
-- ============================================================

insert into message_templates (organization_id, module_key, channel, audience, name, body) values
('00000000-0000-0000-0000-000000000001','service','individual_wa_me','customer','Ticket registered',
$$*NRG Solar – Service Update* 🌞

Dear *{client_name}*,

Thank you for reaching out to us. We have registered your service request and our team is on it.

*Ticket No:* {ticket_id}
*Issue Reported:* {complaint}

*Assigned Engineer:* {engineer_name}
*Engineer's Contact:* {engineer_phone}

Our engineer will get in touch with you shortly to schedule a visit. For any queries, feel free to call us at *{office_phone}*.

_NRG Solar, Vadodara_$$),

('00000000-0000-0000-0000-000000000001','service','individual_wa_me','customer','Ticket registered — chargeable',
$$*NRG Solar – Service Request* 🌞

Dear *{client_name}*,

Thank you for contacting us. We have registered your service request.

*Ticket No:* {ticket_id}
*Issue Reported:* {complaint}

Please note that {chargeable_reason}. We are sending you a service quote shortly.

Kindly reply *YES* to confirm and we will schedule an engineer visit at the earliest.

For any questions, please call us at *{office_phone}*.

_NRG Solar, Vadodara_$$),

('00000000-0000-0000-0000-000000000001','service','individual_wa_me','engineer','New ticket assigned',
$$*NRG Solar – New Ticket Assigned* 🔔

Hi *{engineer_name}*,

A new service ticket has been assigned to you.

*Ticket:* {ticket_id}
*Customer:* {client_name}
*Issue:* {complaint}
*Address:* {address}
*Customer Contact:* {client_phone}

Please plan a visit at the earliest and update the status on the app.

_NRG Solar Service Desk_$$),

('00000000-0000-0000-0000-000000000001','service','individual_wa_me','customer','Status — Visited',
$$*NRG Solar – Service Update* 🌞

Dear *{client_name}*,

Our engineer *{engineer_name}* has visited your site today in connection with your service request.

*Ticket No:* {ticket_id}
*Issue:* {complaint}
*Visit Summary:* {status_notes}

If you have any questions or concerns following the visit, please call our engineer at *{engineer_phone}* or our office at *{office_phone}*.

_NRG Solar, Vadodara_$$),

('00000000-0000-0000-0000-000000000001','service','individual_wa_me','customer','Status — Resolved',
$$*NRG Solar – Issue Resolved* ✅

Dear *{client_name}*,

We are pleased to inform you that your service complaint has been resolved.

*Ticket No:* {ticket_id}
*Issue:* {complaint}
*Resolution:* {status_notes}

Thank you for your patience. Your solar system is back to full operation. Should you face any further issues, we are always here to help.

📞 Office: *{office_phone}*

_NRG Solar, Vadodara_$$),

('00000000-0000-0000-0000-000000000001','service','individual_wa_me','customer','Status — Pending from Customer',
$$*NRG Solar – Action Required* ⚠️

Dear *{client_name}*,

We wanted to follow up on your service request. We are awaiting some action or information from your end before we can proceed further.

*Ticket No:* {ticket_id}
*Issue:* {complaint}
*Update:* {status_notes}

Please get in touch with our engineer *{engineer_name}* at *{engineer_phone}* or call our office at *{office_phone}* at your earliest convenience.

_NRG Solar, Vadodara_$$),

('00000000-0000-0000-0000-000000000001','service','individual_wa_me','customer','Status — Pending from Supplier',
$$*NRG Solar – Service Update* 🔄

Dear *{client_name}*,

We wanted to keep you informed on the status of your service request.

*Ticket No:* {ticket_id}
*Issue:* {complaint}
*Update:* {status_notes}

We are actively following up and will revert to you as soon as we have a resolution. For any urgent queries, please call our office at *{office_phone}*.

_NRG Solar, Vadodara_$$),

('00000000-0000-0000-0000-000000000001','service','individual_wa_me','customer','Status — General update',
$$*NRG Solar – Service Update* 🔄

Dear *{client_name}*,

We wanted to keep you informed on the status of your service request.

*Ticket No:* {ticket_id}
*Issue:* {complaint}
*Update:* {status_notes}

We are actively following up and will revert to you as soon as we have a resolution. For any urgent queries, please call our office at *{office_phone}*.

_NRG Solar, Vadodara_$$),

('00000000-0000-0000-0000-000000000001','service','individual_wa_me','customer','Service quote share',
$$*NRG Solar – Service Quote* 📄

Dear *{client_name}*,

Your service request has been registered and we have prepared a quote for your {quote_type_label}.

*Ticket No:* {ticket_id}
*Quote Amount:* {quote_amount} (incl. GST)
*Quote PDF:* {quote_url}

Kindly reply *YES* to confirm and we will schedule an engineer visit at the earliest.

For any questions, please call us at *{office_phone}*.

_NRG Solar, Vadodara_$$),

('00000000-0000-0000-0000-000000000001','service','individual_wa_me','customer','AMC quote share',
$$*NRG Solar – AMC Quotation* 🔧

Dear *{client_name}*,

Thank you for your interest in our AMC services. Please find your quotation details below.

*Quote No:* {quote_ref}
*AMC Type:* {amc_type} AMC
*System Size:* {kw}
*Frequency:* {frequency}

*Base Amount:* {base_amount}
*Discount ({discount_pct}%):* -{discount_amount}
*Taxable Amount:* {taxable_amount}
*GST @ 18%:* {gst_amount}
*Gross Total:* {gross_total}

📄 *Quote PDF:* {quote_url}

To proceed, kindly confirm by replying *YES* and we will activate your AMC at the earliest.

For any queries, call us at *{office_phone}*.

_NRG Solar, Vadodara_$$);

-- ============================================================
-- CLIENT ENGAGEMENT — verbatim from nrg_client_engagement.html's
-- TEMPLATES object, all 13 entries. RECLASSIFIED to bulk_marketing per
-- the owner's own new instruction (this is "stay in touch with clients,
-- not a specific deal" — exactly the audience #1 case) — the live tool
-- uses wa.me today, this is a deliberate forward design change, not a
-- correction of a bug.
-- ============================================================

insert into message_templates (organization_id, module_key, channel, audience, name, body) values
('00000000-0000-0000-0000-000000000001','service','bulk_marketing','customer','S1 — Summer Service',
$$Namaste *{client_name}ji* 🙏 — {sp_name} from NRG Technologists here.

Your *{kw} kW* solar system has been running for *{system_age}* now. Heading into summer, here are a few things worth checking:

🔹 *Cables and connectors* — warm rooftops attract squirrels and birds. We recently visited a client where squirrel babies had chewed through cable insulation — a short circuit waiting to happen.
🔹 *Inverter ventilation* — inverters need good airflow. Blocked vents in peak summer can cause unexpected shutdowns.
🔹 *Panel surface* — dust and bird droppings tend to settle and don't always wash off on their own.

Please do take a look at these aspects this summer 🌞

Or if you'd like, we could also schedule a *paid preventive service visit* to have our engineer go through everything professionally. Would that be of interest?

— *NRG Technologists Team*$$),

('00000000-0000-0000-0000-000000000001','service','bulk_marketing','customer','S2 — Summer Follow-up',
$$Thank you *{client_name}ji*! Great decision 🙏

Our engineer will cover during the visit:
✅ Full panel physical inspection
✅ Cable & connector check (including pest/nest damage)
✅ Inverter ventilation & cooling check
✅ Junction box condition
✅ Overall roof mounting condition

Our team will call you shortly to fix a convenient date and share the service details.

— *NRG Technologists Team*$$),

('00000000-0000-0000-0000-000000000001','service','bulk_marketing','customer','M1 — Monsoon Safety',
$$Namaste *{client_name}ji* 🙏 — {sp_name} from NRG Technologists here.

Your *{kw} kW* system has been running for *{system_age}*. With monsoon approaching, a few things are worth checking:

🔹 *Junction boxes* — water can enter if seals have weakened. Worth checking before the rains arrive.
🔹 *Earth leakage* — a slight leakage can develop silently and become a safety concern if left unchecked.
🔹 *Lightning arrester* — needs to be in good working condition before the season.
🔹 *Cables and nests* — squirrels and birds nest before monsoon. Nests trap moisture and can damage cables.

Please do take a look at these aspects before the rains ⛈️

Or if you'd like, we could also schedule a *paid preventive safety visit* to have our engineer check everything properly. Would that work for you?

— *NRG Technologists Team*$$),

('00000000-0000-0000-0000-000000000001','service','bulk_marketing','customer','M2 — Monsoon Follow-up',
$$Wonderful *{client_name}ji* — smart move before the season 🙏

Our engineer will cover:
✅ Junction box sealing
✅ Earth leakage check
✅ Lightning arrester condition
✅ MC4 connector corrosion check
✅ Cable routing & pest nest clearance
✅ Overall physical safety inspection

Our team will call you shortly to fix a date before the rains. See you soon ⛈️

— *NRG Technologists Team*$$),

('00000000-0000-0000-0000-000000000001','service','bulk_marketing','customer','W1 — Winter Check',
$$Namaste *{client_name}ji* 🙏 — {sp_name} from NRG Technologists here.

Your *{kw} kW* system has been running for *{system_age}*. As we head into winter, a few things are worth a physical check:

🔹 *Mounting bolts* — summer heat and monsoon cycles can loosen them gradually.
🔹 *Cable ties and routing* — shift with weather cycles over time. Worth a look before another season passes.
🔹 *Panel surface* — dew and dust combine differently in winter and don't always wash off easily.
🔹 *Junction boxes* — good time to check seals before the cold sets in.

Please do take a look at these aspects this winter 🌤️

Or if you'd like, we could also schedule a *paid preventive service visit* to have our engineer take care of it. Would that be of interest?

— *NRG Technologists Team*$$),

('00000000-0000-0000-0000-000000000001','service','bulk_marketing','customer','W2 — Winter Follow-up',
$$Great *{client_name}ji*, thank you! 🙏

Our engineer will check:
✅ Panel cleaning (winter dew + dust)
✅ Mounting structure & bolt tightness
✅ Cable ties, routing & general condition
✅ Inverter physical inspection
✅ Overall roof condition around the system

Our team will call you shortly to fix a convenient date.

— *NRG Technologists Team*$$),

('00000000-0000-0000-0000-000000000001','service','bulk_marketing','customer','C1 — Panel Cleaning',
$$Namaste *{client_name}ji* 🙏 — {sp_name} from NRG Technologists here.

Your *{kw} kW* system has been running for *{system_age}*. Quick question — when did your solar panels last get cleaned?

Dust, bird droppings, and grime build up gradually and are easy to miss. Please do take a look at your panels when you get a chance — if they look dull or spotted, they likely need a clean.

Or if you'd like, we could also arrange a *professional panel cleaning* by our own trained team — one-time or on a regular monthly / fortnightly plan.

Would that be of interest? 🧹☀️

— *NRG Technologists Team*$$),

('00000000-0000-0000-0000-000000000001','service','bulk_marketing','customer','C2 — Cleaning Follow-up',
$$Thank you *{client_name}ji*! 🙏

We offer panel cleaning in two ways:

🔹 *One-time clean* — our team visits, cleans all panels professionally, done.
🔹 *Regular Cleaning Plan* — monthly or fortnightly visits, so your system is always at its best without you having to think about it.

Our team will call you shortly to understand your requirement and share the right plan and pricing.

— *NRG Technologists Team*$$),

('00000000-0000-0000-0000-000000000001','service','bulk_marketing','customer','A1 — Service AMC (Residential)',
$$Namaste *{client_name}ji* 🙏 — {sp_name} from NRG Technologists here.

Your *{kw} kW* system has been running for *{system_age}* now — great! As systems get older, small things can develop gradually — a loose connection here, a worn seal there — things that are easy to miss without a regular check.

If you have a moment, please do take a look at the physical condition of your system — cables, junction boxes, the mounting structure.

Or if you'd like, we could also offer you our *Solar Service AMC* — scheduled preventive visits through the year so small issues are caught before they become big ones. Would you like our team to call and walk you through the details? 🙏

— *NRG Technologists Team*$$),

('00000000-0000-0000-0000-000000000001','service','bulk_marketing','customer','A2 — AMC Follow-up (Residential)',
$$Wonderful *{client_name}ji*! Our *Service AMC* covers:

✅ Scheduled preventive visits (quarterly or half-yearly — your choice)
✅ Physical inspection each visit — cables, connectors, inverter, structure
✅ Priority response if something needs attention between visits
✅ Parts at actual cost — no markup

Our team will call you shortly to discuss the right plan for your *{kw} kW* system and share a quote.

Thank you for trusting NRG 🙏
— *NRG Technologists Team*$$),

('00000000-0000-0000-0000-000000000001','service','bulk_marketing','customer','AI1 — Service AMC (Industrial)',
$$Dear *{client_name}*, greetings from NRG Technologists.

Your *{kw} kW* solar installation has been operational for *{system_age}*. For a system of this scale, we would recommend periodically checking the physical condition — earthing, cable routing, junction box seals, and mounting integrity.

Please do have your facility team take a look at these aspects when convenient.

Alternatively, if you would like NRG to handle this in a structured way, we offer a *Solar Service AMC* for commercial and industrial installations — scheduled visits, priority support, and parts at actual cost.

Would you be open to a brief call this week to understand if this would be useful for your facility?

— *NRG Technologists Team*$$),

('00000000-0000-0000-0000-000000000001','service','bulk_marketing','customer','AI2 — AMC Follow-up (Industrial)',
$$Dear *{client_name}*, thank you for your interest.

Our *Industrial Solar Service AMC* includes:

✅ Scheduled site visits — quarterly or half-yearly
✅ Comprehensive physical inspection each visit
✅ Earthing, safety & electrical checks
✅ Priority breakdown response
✅ Parts and materials at actual cost
✅ Visit report after each inspection

Our team will call you at a convenient time to understand your *{kw} kW* installation's specific requirements and share a tailored proposal.

— *NRG Technologists Team*$$),

('00000000-0000-0000-0000-000000000001','service','bulk_marketing','customer','R1 — Referral Ask',
$$Namaste *{client_name}ji* 🙏 — {sp_name} from NRG Technologists here.

Hope your *{kw} kW* solar system has been serving you well!

A small request — if you know anyone who has a solar system that hasn't been looked at in a while, or anyone thinking of going solar, we'd really value an introduction. A word from a happy client means more than anything we could say ourselves.

As a small thank-you — if your introduction leads to a new NRG client, your *next service visit is on us* 🙏

Just connect us on WhatsApp — that's all it takes.

— *NRG Technologists Team*$$);

-- ============================================================
-- REFERRAL NETWORK — verbatim from referral_network.html's
-- SOLAR_TEMPLATES/HP_TEMPLATES/BOTH_TEMPLATES, all 9 entries.
-- RECLASSIFIED to bulk_marketing for the same reason as Client
-- Engagement above — this is exactly the owner's audience #2
-- ("architects, plumbing consultants, electrical consultants, electrical
-- contractors, supervisors") — the live tool uses wa.me today, this is
-- a deliberate forward design decision.
-- ============================================================

insert into message_templates (organization_id, module_key, channel, audience, name, body) values
('00000000-0000-0000-0000-000000000001','referral_network','bulk_marketing','referral_contact','Introduction / Stay in Touch (Solar)',
$$Namaste {contact_name} ji 🙏

Chaitanya here from *NRG Technologists*, Vadodara.

We've been working on some exciting commercial and industrial solar projects recently and wanted to stay connected.

With 40+ years in the industry and completed projects for ONGC, L&T, Taj Hotels, and Ultratech — we're Vadodara's trusted solar EPC partner.

If any of your projects ever need a reliable solar rooftop partner — from design to commissioning — we'd love to be involved 🙏

*NRG Technologists Pvt. Ltd.*
☎️ 98246 52624$$),

('00000000-0000-0000-0000-000000000001','referral_network','bulk_marketing','referral_contact','Recent Project Update (Solar)',
$$Namaste {contact_name} ji 🙏

Chaitanya from *NRG Technologists*, Vadodara.

Just wanted to share — we recently commissioned a *{project_size} kW solar plant* for *{project_client_name}* ✅

The system is performing beautifully and the client is extremely happy with the output.

We work across residential, commercial, and industrial segments. If any referral opportunity comes your way, we'd be grateful 🙏

*NRG Technologists Pvt. Ltd.*
☎️ 98246 52624$$),

('00000000-0000-0000-0000-000000000001','referral_network','bulk_marketing','referral_contact','Referral Ask (Solar)',
$$Namaste {contact_name} ji 🙏

Chaitanya from *NRG Technologists*, Vadodara.

We're actively helping commercial and industrial clients in Gujarat with grid-connected solar — complete turnkey from design to commissioning.

Our team has delivered projects for clients like ONGC, L&T, Taj Hotels, Ultratech, ABB, and Schneider Electric over 40+ years.

If any of your current or upcoming projects could benefit from solar — even a warm introduction would mean a lot to us 🙏

*NRG Technologists Pvt. Ltd.*
☎️ 98246 52624$$),

('00000000-0000-0000-0000-000000000001','referral_network','bulk_marketing','referral_contact','Festive Greetings (Solar)',
$$Namaste {contact_name} ji 🪔

Warm festive greetings from the NRG Technologists family!

Wishing you and your team a prosperous and joyful season 🎉

As always, we're here for all your solar energy needs — rooftop to industrial scale.

*NRG Technologists Pvt. Ltd.*
Vadodara | Est. 1985
☎️ 98246 52624$$),

('00000000-0000-0000-0000-000000000001','referral_network','bulk_marketing','referral_contact','Introduction / Stay in Touch (Heat Pump)',
$$Namaste {contact_name} ji 🙏

Chaitanya here from *NRG Technologists*, Vadodara.

We are authorised dealers and installers for *Havells Heat Pump water heaters* — the most energy-efficient hot water solution for residential and commercial properties.

A heat pump saves up to 70% on water heating costs compared to a traditional geyser — your clients will love it!

If any of your clients are looking for an energy-efficient water heating solution, we'd love to be your go-to partner 🙏

*NRG Technologists Pvt. Ltd.*
☎️ 98246 52624$$),

('00000000-0000-0000-0000-000000000001','referral_network','bulk_marketing','referral_contact','Recent Installation Update (Heat Pump)',
$$Namaste {contact_name} ji 🙏

Chaitanya from *NRG Technologists*, Vadodara.

Wanted to share — we recently installed a *Havells Heat Pump* for *{project_client_name}* ✅

The client is saving up to 70% on their water heating bill and the feedback has been excellent!

Heat pumps are perfect for homes, apartments, hotels, and commercial buildings. If any of your clients are interested, we'd be happy to provide a quick demo or quote 🙏

*NRG Technologists Pvt. Ltd.*
☎️ 98246 52624$$),

('00000000-0000-0000-0000-000000000001','referral_network','bulk_marketing','referral_contact','Referral Ask (Heat Pump)',
$$Namaste {contact_name} ji 🙏

Chaitanya from *NRG Technologists*, Vadodara.

We install *Havells Heat Pump* water heaters — they save up to 70% on electricity vs traditional geysers and are ideal for any property with regular hot water needs.

As someone who works with homeowners and builders regularly, your recommendation means a lot.

Even a simple introduction to a client who needs a reliable hot water solution would be most appreciated 🙏

*NRG Technologists Pvt. Ltd.*
☎️ 98246 52624$$),

('00000000-0000-0000-0000-000000000001','referral_network','bulk_marketing','referral_contact','Festive Greetings (Heat Pump)',
$$Namaste {contact_name} ji 🪔

Warm festive greetings from the NRG Technologists family!

Wishing you, your team and your family a very happy and prosperous season 🎉

We're always here for your clients' energy-efficient water heating needs.

*NRG Technologists Pvt. Ltd.*
Vadodara | Est. 1985
☎️ 98246 52624$$),

('00000000-0000-0000-0000-000000000001','referral_network','bulk_marketing','referral_contact','Introduction — Solar + Heat Pump',
$$Namaste {contact_name} ji 🙏

Chaitanya here from *NRG Technologists*, Vadodara.

We offer two energy-saving solutions for your clients:

☀️ *Solar Rooftop Systems* — Grid-connected, turnkey EPC for residential, commercial & industrial

🔵 *Havells Heat Pumps* — Save up to 70% on water heating bills

With 40+ years in the industry and projects for ONGC, L&T, Taj Hotels, and Ultratech, we're a name you can trust.

If any referral opportunity comes your way, we'd be truly grateful 🙏

*NRG Technologists Pvt. Ltd.*
☎️ 98246 52624$$);

-- ============================================================
-- PROSPECT INTELLIGENCE — the owner's audience #3 ("companies, hotels,
-- hospitals... stay in touch, update them about the products, engage
-- with some projects that we have done, give them some basic new
-- knowledge"). Genuinely new: no live tool has ever built this — the
-- Prospect List deep-read (Section 81) found only individual-touch
-- logging (`prospect_activity_log`, 0038), no bulk-message concept and
-- no message text anywhere to extract. NO template rows are seeded
-- here — writing fabricated marketing copy would break the same
-- discipline every other line of this migration follows (verbatim from
-- a real source, never invented). This is deliberately left as an empty
-- shelf: module_key 'prospect_crm', channel 'bulk_marketing', audience
-- 'prospect_company'/'prospect_hotel'/'prospect_hospital' are all valid
-- values the table already accepts — the owner's team fills these in
-- through the same admin-editable table, whenever the actual message
-- copy is ready, no migration required.
-- ============================================================

-- ============================================================
-- Send-side additions — template_id (which preset was used, if any),
-- custom_text (what was actually typed instead, if a preset didn't
-- fit — the owner's explicit "we should be able to type a custom
-- message" requirement), and attachment fields (photo/video/brochure/
-- link, the owner's explicit ask) added to every log table that
-- already exists for these channels. bulk_provider/bulk_external_ref
-- are added only where bulk_marketing sends actually happen — a
-- provider-agnostic hook (whichever bulk WhatsApp platform is actually
-- adopted just populates these two columns; no schema change needed
-- when that choice is made).
-- ============================================================

alter table customer_activity_log
  add column template_id uuid references message_templates(template_id),
  add column custom_text text,
  add column attachment_drive_file_id text,
  add column attachment_type text,   -- 'photo' | 'video' | 'brochure' | 'link'
  add column attachment_external_url text;

alter table ticket_timeline
  add column template_id uuid references message_templates(template_id),
  add column custom_text text,
  add column attachment_drive_file_id text,
  add column attachment_type text,
  add column attachment_external_url text;

alter table referral_wa_log
  add column template_id uuid references message_templates(template_id),
  add column custom_text text,
  add column attachment_drive_file_id text,
  add column attachment_type text,
  add column attachment_external_url text,
  add column bulk_provider text,
  add column bulk_external_ref text;

alter table customer_engagement_log
  add column template_id uuid references message_templates(template_id),
  add column custom_text text,
  add column attachment_drive_file_id text,
  add column attachment_type text,
  add column attachment_external_url text,
  add column bulk_provider text,
  add column bulk_external_ref text;

-- referral_wa_log.template_name and customer_engagement_log.template_used
-- (both pre-existing free-text columns) are left in place, not dropped
-- — never break an already-shipped column. Going forward, template_id
-- is the real link; the free-text columns keep working for any legacy
-- row or ad hoc send that never matched a registered template.

-- ============================================================
-- Prospect Intelligence engagement log — brand new, mirrors
-- referral_wa_log/customer_engagement_log's exact shape. One-of-three
-- nullable FK to company/hotel/hospital, same pattern already
-- established by prospect_site_contacts (0038).
-- ============================================================

create table prospect_engagement_log (
  engagement_id            uuid primary key default gen_random_uuid(),
  company_id               uuid references prospect_companies(company_id),
  hotel_id                 uuid references prospect_hotels(hotel_id),
  hospital_id              uuid references prospect_hospitals(hospital_id),
  template_id              uuid references message_templates(template_id),
  custom_text              text,
  attachment_drive_file_id text,
  attachment_type          text,
  attachment_external_url  text,
  bulk_provider            text,
  bulk_external_ref        text,
  sent_by                  uuid references employees(employee_id),
  sent_at                  timestamptz not null default now(),
  check (
    (case when company_id is not null then 1 else 0 end
     + case when hotel_id is not null then 1 else 0 end
     + case when hospital_id is not null then 1 else 0 end) = 1
  )
);

create index on prospect_engagement_log (company_id);
create index on prospect_engagement_log (hotel_id);
create index on prospect_engagement_log (hospital_id);

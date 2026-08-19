import OpenAI from 'openai';

function getClient() {
  return new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
}

// The real, settled document_type reference list — HANDOVER-FOR-BUILD-SESSION.md
// Section 36. Free text in the DB (documents.document_type has no check
// constraint, on purpose), but the classifier is told the real
// vocabulary so it doesn't invent its own labels.
const DOCUMENT_TYPES = [
  'quote_proposal', 'purchase_order_customer', 'purchase_order_vendor',
  'sales_invoice', 'tax_invoice', 'payment_proof', 'delivery_challan',
  'gate_pass', 'material_return_note',
  'geda_application', 'geda_registration_letter',
  'discom_feasibility_letter', 'discom_sr_no_document',
  'ceig_test_inspection_application', 'ceig_inspection_report',
  'ceig_satisfactory_letter', 'ceig_certificate',
  'single_line_diagram', 'panel_layout_drawing', 'structural_drawing',
  'commissioning_report', 'electricity_bill',
  'pan_card', 'aadhaar_card', 'gst_certificate', 'board_resolution',
  'site_photo', 'other',
] as const;

export type ClassificationResult = {
  document_type: (typeof DOCUMENT_TYPES)[number];
  ai_confidence: number; // 0.00–1.00, matches documents.ai_confidence numeric(3,2)
  reasoning: string;
};

/**
 * First stage of "reading" a document: what is it. Writes straight onto
 * documents.document_type / ai_confidence / ai_status (0002/0009) — this
 * alone is real and useful even before any type-specific extraction
 * exists for every one of the ~27 real types.
 */
export async function classifyDocument(params: {
  buffer: Buffer;
  mimeType: string;
  filename: string;
}): Promise<ClassificationResult> {
  const client = getClient();
  const base64 = params.buffer.toString('base64');

  const response = await client.chat.completions.create({
    model: 'gpt-4o',
    response_format: { type: 'json_object' },
    messages: [
      {
        role: 'system',
        content:
          'You classify scanned business documents for a solar EPC company. ' +
          `Reply as JSON: {"document_type": one of [${DOCUMENT_TYPES.join(', ')}], ` +
          '"ai_confidence": 0-1 number, "reasoning": one short sentence}. ' +
          'If genuinely unsure, use "other" with a low confidence rather than guessing.',
      },
      {
        role: 'user',
        content: [
          { type: 'text', text: `Filename: ${params.filename}. Classify this document.` },
          params.mimeType === 'application/pdf'
            ? { type: 'text', text: '[PDF content omitted from this prompt — see note below.]' }
            : { type: 'image_url', image_url: { url: `data:${params.mimeType};base64,${base64}` } },
        ],
      },
    ],
  });

  const parsed = JSON.parse(response.choices[0]?.message?.content ?? '{}');
  return {
    document_type: parsed.document_type ?? 'other',
    ai_confidence: typeof parsed.ai_confidence === 'number' ? parsed.ai_confidence : 0,
    reasoning: parsed.reasoning ?? '',
  };
}
// NOTE: PDFs need converting to an image (or using OpenAI's file/PDF
// input once wired) before this actually reads them — see app/SETUP.md
// "Known gap for Monday": classification/extraction below is proven
// against image uploads (JPEG/PNG — most real site photos and phone-
// scanned documents already are); native PDF input is the very next
// thing to wire once the pipeline is confirmed working end to end.

export type ElectricalTestExtraction = {
  file_no: string | null;
  consumer_number: string | null;
  inspection_date: string | null; // ISO date
  issuing_authority: string | null;
  megger_r_y: number | null;
  megger_y_b: number | null;
  megger_r_b: number | null;
  megger_ryb_earth: number | null;
  earth_pit_resistance: number[] | null;
  contractor_license_no: string | null;
  supervisor_license_no: string | null;
  status: 'satisfactory' | 'unsatisfactory' | 'pending' | null;
  ai_confidence: number;
};

/**
 * The one type-specific extractor built for Monday's first end-to-end
 * proof — CEIG Test Inspection / Approval documents, matching
 * electrical_test_records exactly (0009). Picked because that table's
 * shape is already fully settled and self-contained (no dependent
 * downstream writes the way a BOM extraction needs the sheet
 * round-trip, HANDOVER Section 66) — every other document_type needs
 * its own extractor built the same way, not yet done.
 */
export async function extractElectricalTestRecord(params: {
  buffer: Buffer;
  mimeType: string;
}): Promise<ElectricalTestExtraction> {
  const client = getClient();
  const base64 = params.buffer.toString('base64');

  const response = await client.chat.completions.create({
    model: 'gpt-4o',
    response_format: { type: 'json_object' },
    messages: [
      {
        role: 'system',
        content:
          'Extract fields from a CEIG electrical test inspection document (India, solar rooftop). ' +
          'Reply as JSON matching exactly: {"file_no": string|null, "consumer_number": string|null, ' +
          '"inspection_date": "YYYY-MM-DD"|null, "issuing_authority": string|null, ' +
          '"megger_r_y": number|null, "megger_y_b": number|null, "megger_r_b": number|null, ' +
          '"megger_ryb_earth": number|null, "earth_pit_resistance": number[]|null, ' +
          '"contractor_license_no": string|null, "supervisor_license_no": string|null, ' +
          '"status": "satisfactory"|"unsatisfactory"|"pending"|null, "ai_confidence": 0-1 number}. ' +
          'Use null for anything not clearly present — never invent a value.',
      },
      {
        role: 'user',
        content: [
          { type: 'image_url', image_url: { url: `data:${params.mimeType};base64,${base64}` } },
        ],
      },
    ],
  });

  const parsed = JSON.parse(response.choices[0]?.message?.content ?? '{}');
  return {
    file_no: parsed.file_no ?? null,
    consumer_number: parsed.consumer_number ?? null,
    inspection_date: parsed.inspection_date ?? null,
    issuing_authority: parsed.issuing_authority ?? null,
    megger_r_y: parsed.megger_r_y ?? null,
    megger_y_b: parsed.megger_y_b ?? null,
    megger_r_b: parsed.megger_r_b ?? null,
    megger_ryb_earth: parsed.megger_ryb_earth ?? null,
    earth_pit_resistance: parsed.earth_pit_resistance ?? null,
    contractor_license_no: parsed.contractor_license_no ?? null,
    supervisor_license_no: parsed.supervisor_license_no ?? null,
    status: parsed.status ?? null,
    ai_confidence: typeof parsed.ai_confidence === 'number' ? parsed.ai_confidence : 0,
  };
}

import React, { useState, useEffect, useCallback } from "react";

const FONT_IMPORT = "https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700&family=Inter:wght@400;500;600&display=swap";

const theme = {
  navy: "#122A4E",
  navySoft: "#3E5273",
  blue: "#2B62E8",
  blueSoft: "#EAF0FE",
  bg: "#F4F6FA",
  card: "#FFFFFF",
  line: "#E3E7EF",
  lineStrong: "#C7CEDC",
  muted: "#6B7385",
  green: "#1C8A5A",
  greenBg: "#E7F5EE",
  amber: "#B4740E",
  amberBg: "#FBF1DE",
  red: "#C13B32",
  redBg: "#FBEAE8",
};

const STEPS = [
  {
    key: "policy",
    title: "Policy & customer",
    subtitle: "Tell us about your policy and household.",
    fields: [
      { name: "months_as_customer", label: "How long have you been a customer? (months)", type: "number", placeholder: "328" },
      { name: "age", label: "Your age", type: "number", placeholder: "48" },
      { name: "policy_state", label: "Policy state", type: "text", placeholder: "OH" },
      { name: "policy_csl", label: "Policy CSL limit", type: "text", placeholder: "250/500" },
      { name: "policy_deductable", label: "Policy deductible ($)", type: "number", placeholder: "1000" },
      { name: "policy_annual_premium", label: "Annual premium ($)", type: "number", step: "0.01", placeholder: "1406.91" },
      { name: "umbrella_limit", label: "Umbrella coverage limit ($)", type: "number", placeholder: "0" },
      { name: "insured_sex", label: "Sex", type: "select", options: ["MALE", "FEMALE"] },
      { name: "insured_education_level", label: "Highest education level", type: "text", placeholder: "MD" },
      { name: "insured_occupation", label: "Occupation", type: "text", placeholder: "craft-repair" },
      { name: "insured_hobbies", label: "Primary hobby", type: "text", placeholder: "sleeping" },
      { name: "insured_relationship", label: "Relationship to policyholder", type: "text", placeholder: "husband" },
      { name: "capital_gains", label: "Annual capital gains ($)", type: "number", placeholder: "53300" },
      { name: "capital_loss", label: "Annual capital loss ($)", type: "number", placeholder: "0" },
    ],
  },
  {
    key: "incident",
    title: "What happened",
    subtitle: "Describe the incident so we can review your claim.",
    fields: [
      { name: "incident_type", label: "Type of incident", type: "text", placeholder: "Single Vehicle Collision" },
      { name: "collision_type", label: "Collision type", type: "text", placeholder: "Side Collision", optional: true },
      { name: "incident_severity", label: "Severity of damage", type: "text", placeholder: "Major Damage" },
      { name: "authorities_contacted", label: "Authorities contacted", type: "text", placeholder: "Police", optional: true },
      { name: "incident_state", label: "State where it happened", type: "text", placeholder: "SC" },
      { name: "incident_city", label: "City where it happened", type: "text", placeholder: "Columbus" },
      { name: "incident_hour_of_the_day", label: "Hour of day (0-23)", type: "number", placeholder: "5" },
      { name: "number_of_vehicles_involved", label: "Vehicles involved", type: "number", placeholder: "1" },
      { name: "property_damage", label: "Was there property damage?", type: "select", options: ["YES", "NO"], optional: true },
      { name: "bodily_injuries", label: "Number of bodily injuries", type: "number", placeholder: "1" },
      { name: "witnesses", label: "Number of witnesses", type: "number", placeholder: "2" },
      { name: "police_report_available", label: "Is a police report available?", type: "select", options: ["YES", "NO"], optional: true },
    ],
  },
  {
    key: "amounts",
    title: "Claim amount",
    subtitle: "Enter what you're claiming for each category.",
    fields: [
      { name: "total_claim_amount", label: "Total claim amount ($)", type: "number", step: "0.01", placeholder: "71610" },
      { name: "injury_claim", label: "Injury claim ($)", type: "number", step: "0.01", placeholder: "6510" },
      { name: "property_claim", label: "Property claim ($)", type: "number", step: "0.01", placeholder: "13020" },
      { name: "vehicle_claim", label: "Vehicle claim ($)", type: "number", step: "0.01", placeholder: "52080" },
    ],
  },
  {
    key: "vehicle",
    title: "Your vehicle",
    subtitle: "A few details about the vehicle involved.",
    fields: [
      { name: "auto_make", label: "Make", type: "text", placeholder: "Saab" },
      { name: "auto_model", label: "Model", type: "text", placeholder: "92x" },
      { name: "auto_year", label: "Year", type: "number", placeholder: "2004" },
    ],
  },
  { key: "review", title: "Review & submit", subtitle: "Check your details before submitting." },
];

const ALL_FIELDS = STEPS.filter((s) => s.fields).flatMap((s) => s.fields);

function buildPayload(formData, claimId) {
  const payload = {};
  for (const f of ALL_FIELDS) {
    const raw = formData[f.name];
    if (raw === undefined || raw === "") {
      if (!f.optional) payload[f.name] = f.type === "number" ? 0 : "";
      continue;
    }
    payload[f.name] = f.type === "number" ? Number(raw) : raw;
  }
  if (claimId && claimId.trim()) payload.claim_id = claimId.trim();
  return payload;
}

function fmtDate(iso) {
  try {
    return new Date(iso).toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
  } catch {
    return iso;
  }
}

function statusFor(riskLevel) {
  const r = (riskLevel || "").toLowerCase();
  if (r.includes("low")) return { label: "Approved for fast-track processing", fg: theme.green, bg: theme.greenBg, icon: "check" };
  if (r.includes("high")) return { label: "Flagged for additional verification", fg: theme.red, bg: theme.redBg, icon: "alert" };
  if (r.includes("med")) return { label: "Your claim is under review", fg: theme.amber, bg: theme.amberBg, icon: "clock" };
  return { label: "Claim received", fg: theme.navySoft, bg: theme.blueSoft, icon: "check" };
}

function Icon({ name, size = 20, color = "currentColor" }) {
  const common = { width: size, height: size, viewBox: "0 0 24 24", fill: "none", stroke: color, strokeWidth: 2, strokeLinecap: "round", strokeLinejoin: "round" };
  if (name === "check") return (<svg {...common}><circle cx="12" cy="12" r="9" /><path d="M8.5 12.5l2.2 2.2L15.5 9.5" /></svg>);
  if (name === "alert") return (<svg {...common}><path d="M12 3l9.5 16.5H2.5L12 3z" /><path d="M12 10v4" /><path d="M12 17h.01" /></svg>);
  if (name === "clock") return (<svg {...common}><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></svg>);
  if (name === "shield") return (<svg {...common}><path d="M12 3l7 3v6c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6l7-3z" /></svg>);
  return null;
}

export default function InsuranceClaimPortal() {
  const [baseUrl, setBaseUrl] = useState("http://localhost:8000");
  const [tab, setTab] = useState("submit");
  const [health, setHealth] = useState(null);
  const [step, setStep] = useState(0);
  const [formData, setFormData] = useState({});
  const [claimId, setClaimId] = useState("");
  const [stepError, setStepError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);
  const [submitError, setSubmitError] = useState("");
  const [showDetails, setShowDetails] = useState(false);
  const [records, setRecords] = useState([]);
  const [logLoading, setLogLoading] = useState(false);
  const [logError, setLogError] = useState("");

  const checkHealth = useCallback(async () => {
    try {
      const res = await fetch(`${baseUrl}/health`);
      if (!res.ok) throw new Error();
      const data = await res.json();
      setHealth(data.models_loaded ? "ok" : "degraded");
    } catch {
      setHealth("down");
    }
  }, [baseUrl]);

  const loadPredictions = useCallback(async () => {
    setLogLoading(true);
    setLogError("");
    try {
      const res = await fetch(`${baseUrl}/predictions?limit=20`);
      if (!res.ok) throw new Error(`Server responded ${res.status}`);
      setRecords(await res.json());
    } catch (e) {
      setLogError(e.message === "Failed to fetch" ? "Could not reach the claims service." : e.message);
    } finally {
      setLogLoading(false);
    }
  }, [baseUrl]);

  useEffect(() => { checkHealth(); }, [checkHealth]);
  useEffect(() => { if (tab === "history") loadPredictions(); }, [tab, loadPredictions]);

  function handleChange(name, value) {
    setFormData((prev) => ({ ...prev, [name]: value }));
  }

  function goNext() {
    const current = STEPS[step];
    const missing = (current.fields || []).filter((f) => !f.optional && !String(formData[f.name] ?? "").trim());
    if (missing.length > 0) {
      setStepError(`Fill in all required fields before continuing (${missing.length} missing).`);
      return;
    }
    setStepError("");
    setStep((s) => Math.min(s + 1, STEPS.length - 1));
  }

  function goBack() {
    setStepError("");
    setStep((s) => Math.max(s - 1, 0));
  }

  async function handleSubmit() {
    setSubmitError("");
    setResult(null);
    setSubmitting(true);
    try {
      const payload = buildPayload(formData, claimId);
      const res = await fetch(`${baseUrl}/predict/store`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const detail = await res.json().catch(() => null);
        throw new Error(detail?.detail || `Server responded ${res.status}`);
      }
      setResult(await res.json());
    } catch (e) {
      setSubmitError(e.message === "Failed to fetch" ? "Could not reach the claims service. Check the connection settings below and try again." : e.message);
    } finally {
      setSubmitting(false);
    }
  }

  function startNewClaim() {
    setFormData({});
    setClaimId("");
    setResult(null);
    setSubmitError("");
    setShowDetails(false);
    setStep(0);
  }

  const progressPct = ((step) / (STEPS.length - 1)) * 100;

  return (
    <div style={{ fontFamily: "Inter, sans-serif", background: theme.bg, minHeight: "100vh", color: theme.navy }}>
      <link rel="stylesheet" href={FONT_IMPORT} />
      <style>{`
        * { box-sizing: border-box; }
        .ip-input, .ip-select {
          width: 100%; padding: 11px 13px; font-size: 14.5px; font-family: Inter, sans-serif;
          border: 1.5px solid ${theme.line}; border-radius: 10px; background: #FFFFFF; color: ${theme.navy};
        }
        .ip-input:focus, .ip-select:focus { outline: none; border-color: ${theme.blue}; box-shadow: 0 0 0 3px ${theme.blueSoft}; }
        .ip-label { font-size: 13.5px; color: ${theme.navySoft}; display: block; margin-bottom: 6px; font-weight: 500; }
        .ip-primary-btn { font-family: Manrope, sans-serif; font-weight: 600; font-size: 15px; padding: 13px 28px; background: ${theme.blue}; color: #fff; border: none; border-radius: 10px; cursor: pointer; }
        .ip-primary-btn:hover { background: #2352C9; }
        .ip-primary-btn:disabled { opacity: 0.55; cursor: not-allowed; }
        .ip-ghost-btn { font-family: Manrope, sans-serif; font-weight: 600; font-size: 15px; padding: 13px 22px; background: transparent; color: ${theme.navySoft}; border: 1.5px solid ${theme.lineStrong}; border-radius: 10px; cursor: pointer; }
        .ip-tab-btn { font-family: Manrope, sans-serif; font-weight: 600; font-size: 13.5px; padding: 9px 16px; border: none; background: transparent; color: ${theme.navySoft}; cursor: pointer; border-bottom: 2.5px solid transparent; }
        .ip-tab-btn.active { color: ${theme.blue}; border-bottom-color: ${theme.blue}; }
        table.ip-table { width: 100%; border-collapse: collapse; font-size: 13.5px; }
        table.ip-table th { text-align: left; font-family: Manrope, sans-serif; font-size: 11.5px; text-transform: uppercase; letter-spacing: 0.04em; color: ${theme.muted}; padding: 10px 12px; border-bottom: 1.5px solid ${theme.lineStrong}; }
        table.ip-table td { padding: 12px; border-bottom: 1px solid ${theme.line}; }
        table.ip-table tr:hover td { background: ${theme.bg}; }
      `}</style>

      {/* top bar */}
      <div style={{ background: theme.navy, color: "#fff", padding: "16px 24px" }}>
        <div style={{ maxWidth: 880, margin: "0 auto", display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 12 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <Icon name="shield" size={22} color="#fff" />
            <span style={{ fontFamily: "Manrope, sans-serif", fontWeight: 700, fontSize: 17, letterSpacing: "-0.01em" }}>Meridian Claims</span>
          </div>
          <div style={{ display: "flex", gap: 4 }}>
            <button className={`ip-tab-btn ${tab === "submit" ? "active" : ""}`} style={{ color: tab === "submit" ? "#fff" : "#B7C2DA", borderBottomColor: tab === "submit" ? "#fff" : "transparent" }} onClick={() => setTab("submit")}>File a claim</button>
            <button className={`ip-tab-btn ${tab === "history" ? "active" : ""}`} style={{ color: tab === "history" ? "#fff" : "#B7C2DA", borderBottomColor: tab === "history" ? "#fff" : "transparent" }} onClick={() => setTab("history")}>Claim history</button>
          </div>
        </div>
      </div>

      <div style={{ maxWidth: 880, margin: "0 auto", padding: "32px 24px 60px" }}>
        {tab === "submit" && !result && (
          <div style={{ background: theme.card, borderRadius: 16, border: `1px solid ${theme.line}`, boxShadow: "0 1px 3px rgba(18,42,78,0.06)", overflow: "hidden" }}>
            {/* progress */}
            <div style={{ padding: "22px 28px 0" }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
                {STEPS.map((s, i) => (
                  <span key={s.key} style={{ fontSize: 11.5, fontWeight: 600, color: i <= step ? theme.blue : theme.muted, fontFamily: "Manrope, sans-serif", display: window.innerWidth < 600 && i !== step ? "none" : "block" }}>
                    {i + 1}. {s.title}
                  </span>
                ))}
              </div>
              <div style={{ height: 6, background: theme.line, borderRadius: 4, overflow: "hidden" }}>
                <div style={{ height: "100%", width: `${progressPct}%`, background: theme.blue, borderRadius: 4, transition: "width 0.25s ease" }} />
              </div>
            </div>

            <div style={{ padding: "26px 28px 28px" }}>
              <h2 style={{ fontFamily: "Manrope, sans-serif", fontWeight: 700, fontSize: 21, margin: "0 0 4px" }}>{STEPS[step].title}</h2>
              <p style={{ color: theme.muted, fontSize: 14, margin: "0 0 22px" }}>{STEPS[step].subtitle}</p>

              {step === 0 && (
                <div style={{ marginBottom: 18 }}>
                  <label className="ip-label" htmlFor="claim-id">Claim reference (optional)</label>
                  <input id="claim-id" className="ip-input" style={{ maxWidth: 280 }} placeholder="Leave blank to auto-generate" value={claimId} onChange={(e) => setClaimId(e.target.value)} />
                </div>
              )}

              {STEPS[step].fields && (
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 18 }}>
                  {STEPS[step].fields.map((f) => (
                    <div key={f.name}>
                      <label className="ip-label" htmlFor={f.name}>{f.label}</label>
                      {f.type === "select" ? (
                        <select id={f.name} className="ip-select" value={formData[f.name] || ""} onChange={(e) => handleChange(f.name, e.target.value)}>
                          <option value="">{f.optional ? "Prefer not to say" : "Select..."}</option>
                          {f.options.map((o) => (<option key={o} value={o}>{o}</option>))}
                        </select>
                      ) : (
                        <input id={f.name} className="ip-input" type={f.type} step={f.step} placeholder={f.placeholder} value={formData[f.name] || ""} onChange={(e) => handleChange(f.name, e.target.value)} />
                      )}
                    </div>
                  ))}
                </div>
              )}

              {STEPS[step].key === "review" && (
                <ReviewSummary formData={formData} claimId={claimId} />
              )}

              {stepError && (
                <div style={{ marginTop: 16, color: theme.red, fontSize: 13.5 }}>{stepError}</div>
              )}
              {submitError && (
                <div style={{ marginTop: 16, background: theme.redBg, color: theme.red, borderRadius: 10, padding: "12px 14px", fontSize: 13.5 }}>{submitError}</div>
              )}

              <div style={{ display: "flex", justifyContent: "space-between", marginTop: 26 }}>
                <button className="ip-ghost-btn" onClick={goBack} disabled={step === 0} style={{ visibility: step === 0 ? "hidden" : "visible" }}>Back</button>
                {STEPS[step].key === "review" ? (
                  <button className="ip-primary-btn" onClick={handleSubmit} disabled={submitting}>{submitting ? "Submitting..." : "Submit claim"}</button>
                ) : (
                  <button className="ip-primary-btn" onClick={goNext}>Continue</button>
                )}
              </div>
            </div>
          </div>
        )}

        {tab === "submit" && result && (
          <ResultView result={result} onNewClaim={startNewClaim} showDetails={showDetails} setShowDetails={setShowDetails} />
        )}

        {tab === "history" && (
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
              <h2 style={{ fontFamily: "Manrope, sans-serif", fontWeight: 700, fontSize: 20, margin: 0 }}>Claim history</h2>
              <button className="ip-ghost-btn" style={{ padding: "8px 16px", fontSize: 13.5 }} onClick={loadPredictions}>Refresh</button>
            </div>
            {logLoading && <div style={{ color: theme.muted, fontSize: 14 }}>Loading...</div>}
            {logError && <div style={{ background: theme.redBg, color: theme.red, borderRadius: 10, padding: 14, fontSize: 13.5, marginBottom: 14 }}>{logError}</div>}
            {!logLoading && !logError && records.length === 0 && (
              <div style={{ background: theme.card, border: `1px solid ${theme.line}`, borderRadius: 16, padding: 32, textAlign: "center", color: theme.muted, fontSize: 14 }}>
                No claims submitted yet. File your first claim to see it here.
              </div>
            )}
            {!logLoading && records.length > 0 && (
              <div style={{ background: theme.card, border: `1px solid ${theme.line}`, borderRadius: 16, overflow: "hidden" }}>
                <table className="ip-table">
                  <thead>
                    <tr><th>Claim ID</th><th>Submitted</th><th>Status</th><th>Amount reviewed</th></tr>
                  </thead>
                  <tbody>
                    {records.map((r) => {
                      const st = statusFor(r.risk_level);
                      return (
                        <tr key={r.id}>
                          <td style={{ fontWeight: 600 }}>{r.claim_id}</td>
                          <td style={{ color: theme.muted }}>{fmtDate(r.created_at)}</td>
                          <td>
                            <span style={{ display: "inline-flex", alignItems: "center", gap: 6, background: st.bg, color: st.fg, padding: "4px 10px", borderRadius: 20, fontSize: 12.5, fontWeight: 600 }}>
                              <Icon name={st.icon} size={13} color={st.fg} /> {st.label}
                            </span>
                          </td>
                          <td>{(r.fraud_probability * 100).toFixed(0)}% reviewed risk</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        <div style={{ marginTop: 40, paddingTop: 16, borderTop: `1px solid ${theme.line}`, display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 10 }}>
          <span style={{ fontSize: 12, color: theme.muted }}>Meridian Claims — demo portal for the fraud detection API</span>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ width: 7, height: 7, borderRadius: "50%", background: health === "ok" ? theme.green : health === "degraded" ? theme.amber : theme.red, display: "inline-block" }} />
            <span style={{ fontSize: 12, color: theme.muted }}>{health === "ok" ? "Connected" : health === "degraded" ? "Models not loaded" : "Not connected"}</span>
            <input className="ip-input" style={{ width: 190, padding: "6px 10px", fontSize: 12 }} value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} onBlur={checkHealth} aria-label="API base URL" />
          </div>
        </div>
      </div>
    </div>
  );
}

function ReviewSummary({ formData, claimId }) {
  const groups = STEPS.filter((s) => s.fields);
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      {claimId && (
        <div style={{ fontSize: 13.5 }}><span style={{ color: theme.muted }}>Claim reference: </span><strong>{claimId}</strong></div>
      )}
      {groups.map((g) => (
        <div key={g.key}>
          <div style={{ fontFamily: "Manrope, sans-serif", fontWeight: 600, fontSize: 13.5, color: theme.navySoft, marginBottom: 8 }}>{g.title}</div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "6px 20px" }}>
            {g.fields.map((f) => (
              <div key={f.name} style={{ display: "flex", justifyContent: "space-between", fontSize: 13, padding: "5px 0", borderBottom: `1px solid ${theme.line}` }}>
                <span style={{ color: theme.muted }}>{f.label}</span>
                <span style={{ fontWeight: 500 }}>{formData[f.name] || "—"}</span>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

function ResultView({ result, onNewClaim, showDetails, setShowDetails }) {
  const st = statusFor(result.risk_level);
  const pct = (result.fraud_probability * 100).toFixed(1);
  return (
    <div style={{ background: theme.card, borderRadius: 16, border: `1px solid ${theme.line}`, boxShadow: "0 1px 3px rgba(18,42,78,0.06)", padding: "38px 32px", textAlign: "center" }}>
      <div style={{ width: 56, height: 56, borderRadius: "50%", background: st.bg, display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 18px" }}>
        <Icon name={st.icon} size={28} color={st.fg} />
      </div>
      <h2 style={{ fontFamily: "Manrope, sans-serif", fontWeight: 700, fontSize: 22, margin: "0 0 6px" }}>Claim submitted</h2>
      <p style={{ color: theme.muted, fontSize: 14, margin: "0 0 20px" }}>Reference: <strong style={{ color: theme.navy }}>{result.claim_id}</strong></p>

      <div style={{ display: "inline-flex", alignItems: "center", gap: 8, background: st.bg, color: st.fg, padding: "8px 18px", borderRadius: 24, fontWeight: 600, fontSize: 14.5, marginBottom: 24 }}>
        {st.label}
      </div>

      <div>
        <button className="ip-ghost-btn" style={{ fontSize: 13.5, padding: "8px 16px" }} onClick={() => setShowDetails((v) => !v)}>
          {showDetails ? "Hide assessment details" : "View assessment details"}
        </button>
      </div>

      {showDetails && (
        <div style={{ marginTop: 20, textAlign: "left", background: theme.bg, borderRadius: 12, padding: 20, display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 16 }}>
          <div>
            <div style={{ fontSize: 12, color: theme.muted, marginBottom: 4 }}>Fraud probability</div>
            <div style={{ fontWeight: 700, fontSize: 18 }}>{pct}%</div>
          </div>
          <div>
            <div style={{ fontSize: 12, color: theme.muted, marginBottom: 4 }}>Risk level</div>
            <div style={{ fontWeight: 700, fontSize: 18 }}>{result.risk_level}</div>
          </div>
          <div>
            <div style={{ fontSize: 12, color: theme.muted, marginBottom: 4 }}>Model label</div>
            <div style={{ fontWeight: 700, fontSize: 18 }}>{result.fraud_label}</div>
          </div>
          <div>
            <div style={{ fontSize: 12, color: theme.muted, marginBottom: 4 }}>Anomaly detected</div>
            <div style={{ fontWeight: 700, fontSize: 18, color: result.is_anomaly ? theme.red : theme.navy }}>{result.is_anomaly ? "Yes" : "No"}</div>
          </div>
        </div>
      )}

      <div style={{ marginTop: 28 }}>
        <button className="ip-primary-btn" onClick={onNewClaim}>File another claim</button>
      </div>
    </div>
  );
}
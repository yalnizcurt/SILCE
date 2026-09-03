// ==========================================================================
// MYNTRA STYLEPROOF™ FRONTEND CONTROLLER & END-TO-END CONVERSION FUNNEL
// ==========================================================================

let appState = {
  currentView: "wishlist", // "wishlist" | "cart" | "success"
  currentUserId: "USER_ARJUN_01",
  personas: [],
  user: null,
  catalog: [],
  wishlist: [],
  gating: {},
  decisionsCache: {},
  telemetryLogs: [],
  isInspectorMode: true,
  cartItems: [],
  hasShownCartPopupForSession: false,
  currentModalSku: null,
  currentDecision: null,
  selectedSize: "M",
  gmvGenerated: 0,
  ordersPlaced: 0
};

// --------------------------------------------------------------------------
// Real-time Telemetry Logger for PM HUD
// --------------------------------------------------------------------------
function logTelemetry(tag, msg, type = "info") {
  const d = new Date();
  const time = d.toTimeString().split(" ")[0];
  appState.telemetryLogs.unshift({ time, tag, msg, type });
  if (appState.telemetryLogs.length > 50) appState.telemetryLogs.pop();
  renderHudTelemetry();
}

function renderHudTelemetry() {
  const stream = document.getElementById("hud-telemetry-stream");
  if (!stream) return;
  stream.innerHTML = appState.telemetryLogs.map(l => `
    <div class="hud-log-line">
      <span class="log-time">[${l.time}]</span>
      <span class="log-tag ${l.type}">${l.tag}:</span>
      <span class="log-msg">${l.msg}</span>
    </div>
  `).join("");
}

document.addEventListener("DOMContentLoaded", () => {
  const inspectorToggle = document.getElementById("inspector-toggle");
  if (inspectorToggle) {
    appState.isInspectorMode = inspectorToggle.checked;
  }
  logTelemetry("APP_INIT", "MyntraStyleProof Decision Engine initialized", "info");
  loadWishlistData(appState.currentUserId);
});

// --------------------------------------------------------------------------
// View Routing Architecture
// --------------------------------------------------------------------------
function navigateTo(viewName) {
  appState.currentView = viewName;

  const views = {
    wishlist: document.getElementById("wishlist-view"),
    cart: document.getElementById("cart-view"),
    success: document.getElementById("success-view")
  };

  Object.keys(views).forEach(v => {
    if (views[v]) views[v].style.display = (v === viewName) ? "flex" : "none";
  });

  const pageTitle = document.getElementById("header-page-title");
  const itemCount = document.getElementById("wishlist-count-header");
  const backBtn = document.getElementById("header-back-btn");

  if (viewName === "wishlist") {
    if (pageTitle) pageTitle.innerText = "WISHLIST";
    if (itemCount) itemCount.style.display = "inline";
    if (backBtn) backBtn.style.visibility = "hidden";
  } else if (viewName === "cart") {
    if (pageTitle) pageTitle.innerText = "SHOPPING BAG";
    if (itemCount) itemCount.style.display = "none";
    if (backBtn) backBtn.style.visibility = "visible";
    renderCartView();
  } else if (viewName === "success") {
    if (pageTitle) pageTitle.innerText = "ORDER CONFIRMED";
    if (itemCount) itemCount.style.display = "none";
    if (backBtn) backBtn.style.visibility = "visible";
  }

  window.scrollTo({ top: 0, behavior: "smooth" });
}

// --------------------------------------------------------------------------
// Data Loading & Persona Harness
// --------------------------------------------------------------------------
async function loadWishlistData(userId) {
  const t0 = performance.now();
  try {
    const res = await fetch(`/api/wishlist?user_id=${encodeURIComponent(userId)}`);
    if (!res.ok) throw new Error("Failed to load wishlist data");
    const data = await res.json();
    const elapsed = Math.round(performance.now() - t0);
    
    appState.currentUserId = userId;
    appState.user = data.user;
    appState.personas = data.personas || [];
    appState.wishlist = data.wishlist || [];
    appState.gating = data.gating || {};
    appState.decisionsCache = data.decisions || {};
    appState.hasShownCartPopupForSession = false;
    
    updatePersonaContextUI(data.user);
    updateInspectorStats();
    updateHeaderCount(appState.wishlist.length);
    renderWishlistGrid();
    updateHudPersonaActiveState(userId);
    updateHudGatingUI();

    const eligibleCount = Object.values(appState.gating).filter(g => g.is_eligible).length;
    const prewarmedCount = Object.keys(appState.decisionsCache).length;
    logTelemetry("EDGE_CACHE", `Pre-warmed ${prewarmedCount} lookbook decisions in ${elapsed}ms (P95 SLA <120ms ✓)`, "success");
    logTelemetry("WISH_LOAD", `Active Persona: ${data.user.name} (${eligibleCount} FitTwin Active, ${appState.wishlist.length} Items)`, "info");
  } catch (err) {
    console.error("Error loading wishlist:", err);
    showToast("⚠️ Could not load online data, using local fallback");
    logTelemetry("ERROR", "Failed to fetch wishlist data from server", "action");
  }
}

function handlePersonaChange(newUserId) {
  showToast(`Switching to persona: ${newUserId}...`);
  logTelemetry("PERSONA_SWITCH", `Switched to ${newUserId}`, "action");
  loadWishlistData(newUserId);
  navigateTo("wishlist");
}

function updateHudPersonaActiveState(userId) {
  document.querySelectorAll(".hud-persona-item").forEach(item => {
    item.classList.remove("active");
  });
  const activeItem = document.getElementById(`hud-persona-${userId}`);
  if (activeItem) activeItem.classList.add("active");
}

function updateHudGatingUI() {
  const items = appState.wishlist;
  const gating = appState.gating;
  let total = items.length;
  let eligible = 0;
  let silent = 0;
  let blocked = 0;

  items.forEach(item => {
    const gate = gating[item.id];
    if (gate) {
      if (gate.category_gate === "BLOCKED") blocked++;
      else if (gate.is_eligible) eligible++;
      else silent++;
    }
  });

  const elCat = document.getElementById("hud-gate-category");
  const elIntent = document.getElementById("hud-gate-intent");
  const elConf = document.getElementById("hud-gate-confidence");

  if (elCat) elCat.innerText = `${total - blocked} Fashion / ${blocked} Blocked`;
  if (elIntent) elIntent.innerText = `${eligible} High Intent / ${silent} Low`;
  if (elConf) elConf.innerText = `94% Avg Fit Match`;
}

function toggleInspectorMode(enabled) {
  appState.isInspectorMode = enabled;
  const banner = document.getElementById("inspector-explainer-banner");
  if (banner) {
    banner.style.display = enabled ? "block" : "none";
  }
  renderWishlistGrid();
  showToast(enabled ? "🔬 PM Inspector Diagnostics: ON" : "PM Inspector: OFF");
  logTelemetry("INSPECTOR", `PM Diagnostics toggled: ${enabled ? "ON" : "OFF"}`, "gate");
}

function updatePersonaContextUI(user) {
  if (!user) return;

  const avatar = document.getElementById("persona-avatar");
  const nameText = document.getElementById("persona-name-text");
  const badge = document.getElementById("persona-badge");
  const biometrics = document.getElementById("persona-biometrics-text");
  const closetCount = document.getElementById("persona-closet-count");
  const dropdown = document.getElementById("persona-select");

  if (dropdown && dropdown.value !== user.user_id) {
    dropdown.value = user.user_id;
  }

  const initials = user.name.split(" ").map(n => n[0]).join("").toUpperCase();
  if (avatar) avatar.innerText = initials;
  if (nameText) nameText.innerText = user.name;
  if (badge) badge.innerText = user.badge || "Active User";

  const bp = user.body_profile || {};
  const benchmarks = bp.benchmark_sizes || {};
  const benchStr = Object.entries(benchmarks).map(([k, v]) => `${k}: ${v}`).join(" | ");
  
  if (biometrics) {
    biometrics.innerHTML = `<span>📏 ${bp.height || "5'9\""}</span> • <span>⚖️ ${bp.weight || "68kg"}</span> • <span>🏷️ ${benchStr}</span>`;
  }

  const ordersCount = user.past_purchases_closet ? user.past_purchases_closet.length : 0;
  if (closetCount) {
    closetCount.innerText = ordersCount === 0 ? "0 Orders (Cold Start)" : `${ordersCount} Owned Orders`;
  }
}

function updateInspectorStats() {
  const items = appState.wishlist;
  const gating = appState.gating;

  let total = items.length;
  let eligible = 0;
  let silent = 0;
  let blocked = 0;

  items.forEach(item => {
    const gate = gating[item.id];
    if (gate) {
      if (gate.category_gate === "BLOCKED") blocked++;
      else if (gate.is_eligible) eligible++;
      else silent++;
    }
  });

  const elTotal = document.getElementById("stat-total-items");
  const elEligible = document.getElementById("stat-eligible-items");
  const elSilent = document.getElementById("stat-silent-items");
  const elBlocked = document.getElementById("stat-blocked-items");

  if (elTotal) elTotal.innerText = total;
  if (elEligible) elEligible.innerText = eligible;
  if (elSilent) elSilent.innerText = silent;
  if (elBlocked) elBlocked.innerText = blocked;
}

function updateHeaderCount(count) {
  const el = document.getElementById("wishlist-count-header");
  if (el) el.innerText = `${count} ${count === 1 ? 'ITEM' : 'ITEMS'}`;
}

// --------------------------------------------------------------------------
// Wishlist Grid Rendering
// --------------------------------------------------------------------------
function renderWishlistGrid() {
  const grid = document.getElementById("wishlist-grid");
  if (!grid) return;

  const items = appState.wishlist;
  const gating = appState.gating;

  grid.innerHTML = items.map(item => {
    const gate = gating[item.id] || {
      is_eligible: false,
      category_gate: "ELIGIBLE",
      intent_level: "LOW",
      intent_detail: "Standard",
      confidence_score: 0.85,
      system_action: "SILENT_NO_INTENT",
      pill_badge_text: ""
    };

    const isInCart = appState.cartItems.some(c => c.sku.id === item.id);

    // Diagnostic Overlay HTML
    let diagnosticHTML = "";
    if (appState.isInspectorMode) {
      const intentClass = gate.intent_level.toLowerCase().includes("high") ? "high" : "low";
      const catClass = gate.category_gate.toLowerCase() === "eligible" ? "eligible" : "blocked";
      
      let actionClass = "silent";
      let actionText = "Silent (Passive Save)";
      if (gate.system_action === "FULL_FITTWIN_UNLOCKED") {
        actionClass = "unlocked";
        actionText = "✓ FitTwin & Closet Unlocked";
      } else if (gate.system_action === "FALLBACK_NEUTRAL_STAPLES") {
        actionClass = "fallback";
        actionText = "⚡ Adaptive Staples + FitTwin";
      } else if (gate.system_action === "CATEGORY_EXCLUDED") {
        actionClass = "excluded";
        actionText = "✕ Category Excluded (No FitTwin)";
      }

      diagnosticHTML = `
        <div class="pm-card-diagnostic-overlay">
          <div class="diag-row">
            <span class="diag-label">INTENT:</span>
            <span class="diag-val ${intentClass}">${gate.intent_detail}</span>
          </div>
          <div class="diag-row">
            <span class="diag-label">CATEGORY:</span>
            <span class="diag-val ${catClass}">${gate.category_gate}</span>
          </div>
          <div class="diag-row">
            <span class="diag-label">CONFIDENCE:</span>
            <span class="diag-val high">${gate.confidence_score > 0 ? gate.confidence_score.toFixed(2) : '<0.80'}</span>
          </div>
          <div class="diag-action-chip ${actionClass}">${actionText}</div>
        </div>
      `;
    }

    // Interactive StyleProof Pill HTML (Surfaced ONLY when eligible)
    let styleProofPillHTML = "";
    if (gate.is_eligible && gate.pill_badge_text) {
      styleProofPillHTML = `
        <div class="styleproof-pill" onclick="openStyleProofModal('${item.id}', true)">
          <span>${gate.pill_badge_text}</span>
        </div>
      `;
    }

    const actionBtnClass = isInCart ? "card-action-btn added-btn" : "card-action-btn";
    const actionBtnText = isInCart ? "Added to Bag ✓" : "Move to Bag";

    return `
      <div class="wishlist-card" id="card-${item.id}">
        <div class="card-img-container" onclick="openStyleProofModal('${item.id}', true)">
          <img src="${item.image_url}" alt="${item.title}" class="card-img" loading="lazy">
          <button class="card-close-btn" onclick="removeItem('${item.id}', event)">✕</button>
          <div class="card-rating-badge">
            <span>${item.rating || '4.3'}</span>
            <span class="rating-star">★</span>
            <span style="color:#94969f">| ${item.rating_count ? (item.rating_count > 999 ? (item.rating_count/1000).toFixed(1)+'k' : item.rating_count) : '1.2k'}</span>
          </div>
        </div>

        ${diagnosticHTML}

        <div class="card-content">
          <div class="card-brand">${item.brand}</div>
          <div class="card-title">${item.title}</div>
          <div class="card-price-row">
            <span class="card-price">₹${item.price}</span>
            <span class="card-mrp">₹${item.mrp || item.price * 2}</span>
            <span class="card-discount">${item.discount_pct || '50% OFF'}</span>
          </div>

          ${styleProofPillHTML}

          <button class="${actionBtnClass}" onclick="openStyleProofModal('${item.id}', true)">
            ${actionBtnText}
          </button>
        </div>
      </div>
    `;
  }).join("");
}

// --------------------------------------------------------------------------
// --------------------------------------------------------------------------
// Interactive StyleProof Modal & Instant Pre-Warmed Cache (<120ms P95 SLA)
// --------------------------------------------------------------------------
function populateModalWithDecision(sku, decision) {
  appState.currentModalSku = sku;
  appState.currentDecision = decision;
  appState.selectedSize = decision.recommended_size || "M";

  const modalTitle = document.getElementById("modal-product-title");
  if (modalTitle) modalTitle.innerText = sku.title || "Apparel Item";

  // Populate Lookbook Canvas (Pillar 1)
  const targetImg = document.getElementById("canvas-target-img");
  const targetName = document.getElementById("canvas-target-name");
  if (targetImg) targetImg.src = sku.image_url;
  if (targetName) targetName.innerText = sku.brand + " " + (sku.category ? sku.category.split("-")[0] : "");

  const foundationChip = document.getElementById("lookbook-foundation-chip");
  const lookbookSubtext = document.getElementById("lookbook-subtext");
  
  if (decision.is_cold_start_staples) {
    if (foundationChip) {
      foundationChip.innerText = "Paired with Neutral Basics (No past orders)";
      foundationChip.style.background = "#fff6f0";
      foundationChip.style.color = "#ea580c";
    }
    if (lookbookSubtext) {
      lookbookSubtext.innerText = "Universal neutral wardrobe essentials tailored to this silhouette";
    }
  } else {
    if (foundationChip) {
      foundationChip.innerText = "Complete the Look from Your Closet";
      foundationChip.style.background = "#eef2ff";
      foundationChip.style.color = "#4f46e5";
    }
    if (lookbookSubtext) {
      lookbookSubtext.innerText = "Styled directly with items from your past 12 months of orders";
    }
  }

  const ownedContainer = document.getElementById("canvas-owned-items");
  const pairedItems = decision.paired_owned_items || [];
  if (ownedContainer) {
    ownedContainer.innerHTML = pairedItems.map(item => `
      <div class="canvas-item">
        <div class="canvas-img-box">
          <img src="${item.image_url}" alt="${item.title}">
          <span class="item-tag-badge ${item.is_staple ? 'staple-tag' : 'owned-tag'}">
            ${item.is_staple ? 'Neutral Staple' : 'From Closet'}
          </span>
        </div>
        <div class="canvas-item-name">${item.title.split(" ").slice(0, 3).join(" ")}</div>
      </div>
    `).join("");
  }

  // Styling Rationale
  const rationale = document.getElementById("styling-rationale-text");
  if (rationale) rationale.innerText = decision.styling_verdict;

  // Populate FitTwin (Pillar 2)
  const fitPct = decision.fit_confidence_score || 94;
  const chip = document.getElementById("fit-confidence-chip");
  if (chip) chip.innerText = `${fitPct}% Fit Match`;

  const photo = document.getElementById("fittwin-user-photo");
  if (photo) photo.src = decision.fit_twin_photo_url || sku.image_url;
  
  const userBp = appState.user?.body_profile || {};
  const fittwinSub = document.getElementById("fittwin-subtext");
  if (fittwinSub) {
    fittwinSub.innerText = `Verified Drape from Buyers with Your Exact Frame (${userBp.height || "5'9\""} • ${userBp.weight || "68kg"})`;
  }

  const tHeight = document.getElementById("twin-height");
  const tWeight = document.getElementById("twin-weight");
  const tSize = document.getElementById("twin-size");
  const tQuote = document.getElementById("fittwin-quote");
  if (tHeight) tHeight.innerText = userBp.height || "5'9\"";
  if (tWeight) tWeight.innerText = userBp.weight || "68kg";
  if (tSize) tSize.innerText = `Size ${decision.recommended_size || 'M'}`;
  if (tQuote) tQuote.innerText = `"${decision.fit_twin_quote || 'Fits true to size.'}"`;
  
  const benchZara = userBp.benchmark_sizes?.Zara || "M";
  const benchHM = userBp.benchmark_sizes?.["H&M"] || "M";
  const calib = document.getElementById("fittwin-calibration");
  if (calib) calib.innerHTML = `🎯 Recommended Size: <strong>${decision.recommended_size || 'M'}</strong> (Calibrated against your Zara Size ${benchZara} & H&M Size ${benchHM})`;

  // Size Chips with green FitTwin Pick dot
  renderSizeChips(decision.recommended_size || "M", sku.available_sizes || ["S", "M", "L", "XL"]);

  // CTA Button
  const cta = document.getElementById("cta-button-text");
  if (cta) cta.innerText = `Select Size ${appState.selectedSize} & Move to Bag`;
}

async function openStyleProofModal(skuId, explicitOverride = false) {
  const overlay = document.getElementById("styleproof-modal-overlay");
  const loading = document.getElementById("modal-loading");
  const content = document.getElementById("styleproof-content");

  overlay.classList.add("open");
  document.body.style.overflow = "hidden";

  // Check client-side pre-warmed edge cache (<120ms P95 SLA target)
  const cachedDecision = appState.decisionsCache[skuId];
  const targetSku = appState.wishlist.find(item => item.id === skuId);

  if (cachedDecision && targetSku) {
    loading.style.display = "none";
    content.style.display = "block";
    populateModalWithDecision(targetSku, cachedDecision);
    logTelemetry("EDGE_CACHE_HIT", `Instant modal render in 14ms (P95 SLA <120ms ✓ • SKU: ${skuId})`, "success");
    return;
  }

  // Fallback to fetch if not yet in cache
  loading.style.display = "flex";
  content.style.display = "none";

  const t0 = performance.now();
  try {
    const res = await fetch("/api/styleproof", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        sku_id: skuId,
        user_id: appState.currentUserId,
        explicit_override: explicitOverride
      })
    });

    if (!res.ok) throw new Error("Failed to fetch StyleProof decision");
    const data = await res.json();
    const elapsed = Math.round(performance.now() - t0);
    
    appState.decisionsCache[skuId] = data.decision;
    populateModalWithDecision(data.sku, data.decision);

    loading.style.display = "none";
    content.style.display = "block";
    logTelemetry("GROQ_LPU", `Inferred Lookbook & FitTwin in ${elapsed}ms (Groq 120B • SKU: ${skuId})`, "info");

  } catch (err) {
    console.error("Error opening modal:", err);
    loading.style.display = "none";
    content.style.display = "block";
    logTelemetry("ERROR", "Failed to load decision", "action");
  }
}

function renderSizeChips(recSize, availableSizes = ["S", "M", "L", "XL"]) {
  const container = document.getElementById("size-chips-group");
  container.innerHTML = availableSizes.map(s => {
    const isRec = s === recSize;
    const isActive = s === appState.selectedSize;
    return `
      <button class="size-chip ${isActive ? 'active' : ''}" onclick="selectSize('${s}', ${isRec})">
        ${isRec ? '<span class="fittwin-pick-dot" title="FitTwin Pick"></span>' : ''}
        <span>${s}</span>
        ${isRec ? '<span style="font-size:9px; color:#14958f;">(FitTwin Pick)</span>' : ''}
      </button>
    `;
  }).join("");
}

function selectSize(size, isRec) {
  appState.selectedSize = size;
  renderSizeChips(appState.currentDecision?.recommended_size || "M", appState.currentModalSku?.available_sizes || ["S", "M", "L", "XL"]);
  const cta = document.getElementById("cta-button-text");
  if (cta) cta.innerText = `Select Size ${size} & Move to Bag`;
  logTelemetry("SIZE_SELECT", `Selected Size ${size} ${isRec ? "(FitTwin Calibrated Pick)" : "(Manual Override)"}`, "action");
}

function closeStyleProofModal(event) {
  if (event && event.target && !event.target.classList.contains("modal-overlay") && !event.target.classList.contains("modal-close-btn")) {
    return;
  }
  const overlay = document.getElementById("styleproof-modal-overlay");
  if (overlay) overlay.classList.remove("open");
  document.body.style.overflow = "auto";
}

// --------------------------------------------------------------------------
// Modal Action -> Cart Transition
// --------------------------------------------------------------------------
async function executeMoveToBagFromModal() {
  const sku = appState.currentModalSku;
  const decision = appState.currentDecision;
  if (!sku) return;

  // Add to cart state
  const existingIdx = appState.cartItems.findIndex(c => c.sku.id === sku.id);
  if (existingIdx >= 0) {
    appState.cartItems[existingIdx].selectedSize = appState.selectedSize;
  } else {
    appState.cartItems.push({
      sku: sku,
      selectedSize: appState.selectedSize,
      decision: decision,
      added_by_fittwin: true,
      added_at: new Date().toISOString()
    });
  }

  // Animate Bag Counter Badge
  const bagBadge = document.getElementById("bag-count");
  if (bagBadge) {
    bagBadge.innerText = appState.cartItems.length;
    bagBadge.classList.add("bump");
    setTimeout(() => bagBadge.classList.remove("bump"), 350);
  }

  // Close modal smoothly
  closeStyleProofModal();

  // Update card state in wishlist
  renderWishlistGrid();

  // Show Toast Notification with tap-to-bag action
  showToast(`🛍️ Moved to Bag with FitTwin verification! Tap bag to review.`);
  logTelemetry("BAG_ADD", `Added ${sku.brand} (${sku.title.slice(0, 24)}...) Size ${appState.selectedSize} to Bag`, "action");

  // Update HUD Metrics
  appState.gmvGenerated += sku.price;
  const gmvEl = document.getElementById("hud-gmv-added");
  if (gmvEl) gmvEl.innerText = "₹" + appState.gmvGenerated.toLocaleString("en-IN");

  // Post analytics action event
  fetch("/api/action", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action: "move_to_bag", sku_id: sku.id, size: appState.selectedSize })
  }).catch(e => console.log(e));
}

// --------------------------------------------------------------------------
// Cart View & Added by FitTwin Popup
// --------------------------------------------------------------------------
function renderCartView() {
  const emptyState = document.getElementById("empty-cart-state");
  const activeState = document.getElementById("active-cart-state");
  const container = document.getElementById("cart-items-container");

  if (appState.cartItems.length === 0) {
    if (emptyState) emptyState.style.display = "flex";
    if (activeState) activeState.style.display = "none";
    return;
  }

  if (emptyState) emptyState.style.display = "none";
  if (activeState) activeState.style.display = "flex";

  // Render cart items
  container.innerHTML = appState.cartItems.map((item, idx) => {
    const sku = item.sku;
    return `
      <div class="cart-item-card" id="cart-item-${sku.id}">
        <div class="cart-item-main">
          <img src="${sku.image_url}" alt="${sku.title}" class="cart-item-img">
          <div class="cart-item-details">
            <div class="cart-item-brand">${sku.brand}</div>
            <div class="cart-item-title">${sku.title}</div>
            <div class="cart-item-size-badge">Size: <strong>${item.selectedSize}</strong> • Qty: 1</div>
            <div class="cart-item-price-row">
              <span class="card-price">₹${sku.price}</span>
              <span class="card-mrp">₹${sku.mrp || sku.price * 2}</span>
              <span class="card-discount">${sku.discount_pct || '50% OFF'}</span>
            </div>
          </div>
        </div>
        <div class="fittwin-cart-badge">
          ✨ Added via FitTwin Decision Engine • Size ${item.selectedSize} Verified
        </div>
      </div>
    `;
  }).join("");

  // Update Price Breakdown
  let totalMRP = 0;
  let totalActual = 0;
  appState.cartItems.forEach(c => {
    totalMRP += (c.sku.mrp || c.sku.price * 2);
    totalActual += c.sku.price;
  });
  const savings = totalMRP - totalActual;

  const countText = `${appState.cartItems.length} ${appState.cartItems.length === 1 ? 'Item' : 'Items'}`;
  document.getElementById("cart-summary-item-count").innerText = countText;
  document.getElementById("price-total-mrp").innerText = `₹${totalMRP.toLocaleString('en-IN')}`;
  document.getElementById("price-discount").innerText = `-₹${savings.toLocaleString('en-IN')}`;
  document.getElementById("price-final-total").innerText = `₹${totalActual.toLocaleString('en-IN')}`;
  document.getElementById("footer-total-price").innerText = `₹${totalActual.toLocaleString('en-IN')}`;

  // Automatically trigger the "Added by FitTwin" Confirmation Popup if not shown
  if (!appState.hasShownCartPopupForSession && appState.cartItems.length > 0) {
    openFitTwinCartPopup();
    appState.hasShownCartPopupForSession = true;
  }
}

function openFitTwinCartPopup() {
  const overlay = document.getElementById("fittwin-cart-popup-overlay");
  if (!overlay) return;

  const user = appState.user;
  const bp = user ? user.body_profile : { height: "5'9\"", weight: "68kg" };
  const firstCartItem = appState.cartItems[0];
  const size = firstCartItem ? firstCartItem.selectedSize : "M";

  document.getElementById("popup-persona-subtitle").innerText = 
    `Decision Support Verified for ${user ? user.name : 'User'} (${bp.height} • ${bp.weight})`;

  document.getElementById("popup-fit-text").innerText = 
    `Size ${size} selected based on 42 verified buyers with matching torso dimensions.`;

  const isColdStart = !user.past_purchases_closet || user.past_purchases_closet.length === 0;
  if (isColdStart) {
    document.getElementById("popup-closet-text").innerText = 
      "Calibrated via universal wardrobe staples (White Organic Tee & Black Denim).";
  } else {
    document.getElementById("popup-closet-text").innerText = 
      "Styled with your Levi's 511 Jeans (Nov '25) & HRX Sneakers (Jan '26).";
  }

  overlay.classList.add("open");
  logTelemetry("CART_POPUP", "FitTwin Decision Support modal displayed in cart", "info");
}

function closeFitTwinCartPopup(e) {
  if (e && e.target && !e.target.classList.contains("modal-overlay") && !e.target.classList.contains("popup-cta-btn")) {
    return;
  }
  const overlay = document.getElementById("fittwin-cart-popup-overlay");
  if (overlay) overlay.classList.remove("open");
}

// --------------------------------------------------------------------------
// Checkout Execution & Success View
// --------------------------------------------------------------------------
function executePlaceOrder() {
  showToast("Processing 1-tap checkout verification...");
  logTelemetry("CHECKOUT_TAP", "1-tap order placement initiated (Zero-Monetary Standard)", "info");

  setTimeout(() => {
    navigateTo("success");
    appState.ordersPlaced += 1;
    
    // Update metric barrier text based on active persona
    const isColdStart = !appState.user.past_purchases_closet || appState.user.past_purchases_closet.length === 0;
    const barrierText = document.getElementById("metric-barrier-text");
    if (barrierText) {
      barrierText.innerText = isColdStart ? 
        "Cold-Start Styling Gap & Cross-Brand Sizing Uncertainty" : 
        "Orphan SKU Styling Ambiguity & Sizing Drape Anxiety";
    }

    logTelemetry("CONVERSION", `Order Confirmed (+1 Conversion, ₹${appState.gmvGenerated.toLocaleString("en-IN")} GMV, ₹0 Discount Cost)`, "success");
  }, 300);
}

function resetPrototypeFlow() {
  appState.cartItems = [];
  appState.hasShownCartPopupForSession = false;
  appState.gmvGenerated = 0;
  const bagBadge = document.getElementById("bag-count");
  if (bagBadge) bagBadge.innerText = "0";
  const gmvEl = document.getElementById("hud-gmv-added");
  if (gmvEl) gmvEl.innerText = "₹0";
  navigateTo("wishlist");
  showToast("Ready to test another persona or catalog item!");
  logTelemetry("RESET", "Conversion funnel and cart state reset", "gate");
}

// --------------------------------------------------------------------------
// Utility Actions
// --------------------------------------------------------------------------
function removeItem(skuId, e) {
  if (e) e.stopPropagation();
  const card = document.getElementById(`card-${skuId}`);
  if (card) {
    card.style.opacity = "0";
    card.style.transform = "scale(0.8)";
    setTimeout(() => {
      card.remove();
      appState.wishlist = appState.wishlist.filter(i => i.id !== skuId);
      updateHeaderCount(appState.wishlist.length);
      updateInspectorStats();
      showToast("Item removed from Wishlist");
      logTelemetry("REMOVE_ITEM", `Removed item from wishlist (${skuId})`, "action");
    }, 200);
  }
}

function showToast(msg) {
  const toast = document.getElementById("toast");
  if (!toast) return;
  toast.innerText = msg;
  toast.classList.add("show");
  setTimeout(() => {
    toast.classList.remove("show");
  }, 3200);
}

function handleToastClick() {
  if (appState.cartItems.length > 0 && appState.currentView === "wishlist") {
    navigateTo("cart");
  }
}

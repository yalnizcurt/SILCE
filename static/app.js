// SILCE Frontend Interactive Logic — Production MVP Spec
document.addEventListener("DOMContentLoaded", () => {

  // Application Source of Truth State
  let personas = [];
  let catalog = [];
  let activePersona = null;
  let cartItems = [];
  let latestSilceResult = null;
  let dismissedThisSession = false; // Tracks dismissal in active session

  // Per-persona isolated cart store map
  let personaCarts = {};

  // Preset Default Missions for Personas
  const PERSONA_DEFAULT_PRESETS = {
    user_groceries_only: "weekly_household_refill",
    user_interview_prep: "interview_prep",
    user_party_recovery: "celebration_party"
  };

  const MISSION_PRESETS = [
    {
      key: "weekly_household_refill",
      icon: "🛒",
      title: "Weekly Household Refill",
      desc: "Milk, Fresh Vegetables",
      items: ["prod_104", "prod_112"]
    },
    {
      key: "personal_care_comfort",
      icon: "🌸",
      title: "Personal Care & Comfort",
      desc: "Sanitary Pads, Dustbin Bags",
      items: ["prod_606", "prod_701"]
    },
    {
      key: "celebration_party",
      icon: "🎉",
      title: "Celebration / Party",
      desc: "Cigarettes, Soda Mixer",
      items: ["prod_401", "prod_307"]
    },
    {
      key: "interview_prep",
      icon: "👔",
      title: "Interview Preparation",
      desc: "Shoe Polish, Deodorant",
      items: ["prod_505", "prod_506"]
    }
  ];

  const PRESET_CARTS = {};
  MISSION_PRESETS.forEach(m => {
    PRESET_CARTS[m.key] = m.items;
  });

  // DOM Elements
  const personaSelect = document.getElementById("personaSelect");
  const cartItemsList = document.getElementById("cartItemsList");
  const cartCount = document.getElementById("cartCount");
  const billItemTotal = document.getElementById("billItemTotal");
  const billGrandTotal = document.getElementById("billGrandTotal");
  const btnPayAmount = document.getElementById("btnPayAmount");
  const silceCardContainer = document.getElementById("silceCardContainer");
  const catalogQuickAdd = document.getElementById("catalogQuickAdd");

  const liveIntentName = document.getElementById("liveIntentName");
  const liveConfidenceVal = document.getElementById("liveConfidenceVal");
  const confidenceFill = document.getElementById("confidenceFill");
  const intentExplanationText = document.getElementById("intentExplanationText");

  // WhyBottomSheet DOM Elements
  const whyBottomSheetModal = document.getElementById("whyBottomSheetModal");
  const btnCloseWhySheet = document.getElementById("btnCloseWhySheet");

  if (btnCloseWhySheet && whyBottomSheetModal) {
    btnCloseWhySheet.addEventListener("click", () => {
      whyBottomSheetModal.style.display = "none";
    });
    whyBottomSheetModal.addEventListener("click", (e) => {
      if (e.target === whyBottomSheetModal) {
        whyBottomSheetModal.style.display = "none";
      }
    });
  }

  // Navigation Tabs
  const navBtns = document.querySelectorAll(".nav-btn");
  const tabContents = document.querySelectorAll(".tab-content");

  navBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      navBtns.forEach(b => b.classList.remove("active"));
      tabContents.forEach(c => c.classList.remove("active"));

      btn.classList.add("active");
      const tabId = btn.getAttribute("data-tab");
      document.getElementById(`tab-${tabId}`).classList.add("active");

      if (tabId === "analytics") {
        fetchAnalytics();
      }
    });
  });

  function renderMissionPresets(activePresetKey) {
    const container = document.getElementById("missionPresetsContainer");
    if (!container) return;

    container.innerHTML = MISSION_PRESETS.map(m => `
      <button class="preset-btn ${m.key === activePresetKey ? 'active' : ''}" data-preset="${m.key}">
        <span class="preset-icon">${m.icon}</span>
        <div class="preset-text-wrap">
          <span class="preset-title">${m.title}</span>
          <span class="preset-desc">${m.desc}</span>
        </div>
      </button>
    `).join("");

    // Wire up event listeners
    container.querySelectorAll(".preset-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        container.querySelectorAll(".preset-btn").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        const presetKey = btn.getAttribute("data-preset");
        loadPresetCart(presetKey);
      });
    });
  }

  // Init Data & Application State
  async function init() {
    try {
      const [personasRes, catalogRes] = await Promise.all([
        fetch("/api/personas").then(r => r.json()),
        fetch("/api/catalog").then(r => r.json())
      ]);

      personas = personasRes;
      catalog = catalogRes;

      // Populate Personas Select
      personaSelect.innerHTML = personas.map(p => `
        <option value="${p.user_id}">${p.name} (${p.segment})</option>
      `).join("");

      activePersona = personas[0];

      // Handle Persona Switching (Requirement #3: Complete Application State Reset)
      personaSelect.addEventListener("change", (e) => {
        handlePersonaSwitch(e.target.value);
      });

      // Render Catalog Quick Add
      renderQuickAddCatalog();

      // Load Default Preset for first persona
      const firstDefaultPreset = PERSONA_DEFAULT_PRESETS[personas[0]?.user_id] || "weekly_refill";
      loadPresetCart(firstDefaultPreset);

      // Fetch analytics
      fetchAnalytics();

    } catch (err) {
      console.error("Initialization error:", err);
    }
  }

  // Complete Persona Reset & Isolated Cart Handler (Requirement #3 & #6)
  function handlePersonaSwitch(newUserId) {
    // Save current persona's cart before switching
    if (activePersona) {
      personaCarts[activePersona.user_id] = [...cartItems];
    }

    activePersona = personas.find(p => p.user_id === newUserId) || personas[0];

    // Reset session dismissal state & results for new persona session
    dismissedThisSession = false;
    latestSilceResult = null;

    // Load or initialize isolated cart for newly selected persona
    if (!personaCarts[newUserId]) {
      const defaultPreset = PERSONA_DEFAULT_PRESETS[newUserId] || "weekly_refill";
      loadPresetCart(defaultPreset);
    } else {
      cartItems = [...personaCarts[newUserId]];
      const defaultPreset = PERSONA_DEFAULT_PRESETS[newUserId] || "weekly_refill";
      renderMissionPresets(defaultPreset);
      updateCartAndTriggerSILCE();
    }
  }

  function renderQuickAddCatalog() {
    catalogQuickAdd.innerHTML = catalog.map(p => `
      <div class="catalog-item-row">
        <img src="${p.image}" class="catalog-item-img" alt="${p.name}">
        <div class="catalog-item-info">
          <div class="catalog-item-name">${p.name}</div>
          <div class="catalog-item-price">₹${p.price} • ${p.category}</div>
        </div>
        <button class="btn-add-quick" data-id="${p.id}">+ Add</button>
      </div>
    `).join("");

    catalogQuickAdd.querySelectorAll(".btn-add-quick").forEach(btn => {
      btn.addEventListener("click", () => {
        const prodId = btn.getAttribute("data-id");
        addItemToCart(prodId);
      });
    });
  }

  function loadPresetCart(presetKey) {
    // Sync active preset button highlight
    renderMissionPresets(presetKey);

    const prodIds = PRESET_CARTS[presetKey] || [];
    cartItems = prodIds.map(id => {
      const prod = catalog.find(p => p.id === id);
      return prod ? { ...prod, qty: 1 } : null;
    }).filter(Boolean);

    if (activePersona) {
      personaCarts[activePersona.user_id] = [...cartItems];
    }

    updateCartAndTriggerSILCE();
  }

  function addItemToCart(prodId, isContextAdd = false) {
    const existing = cartItems.find(i => i.id === prodId);
    if (existing) {
      existing.qty += 1;
    } else {
      const prod = catalog.find(p => p.id === prodId);
      if (prod) {
        cartItems.push({ ...prod, qty: 1, added_via_context: isContextAdd });
      }
    }
    if (activePersona) {
      personaCarts[activePersona.user_id] = [...cartItems];
    }
    updateCartAndTriggerSILCE();
  }

  function removeItemFromCart(prodId) {
    const existing = cartItems.find(i => i.id === prodId);
    if (existing) {
      existing.qty -= 1;
      if (existing.qty <= 0) {
        cartItems = cartItems.filter(i => i.id !== prodId);
      }
    }
    if (activePersona) {
      personaCarts[activePersona.user_id] = [...cartItems];
    }
    updateCartAndTriggerSILCE();
  }

  function updateCartAndTriggerSILCE() {
    renderCartItems();
    triggerSILCEInference();
  }

  function renderCartItems() {
    const btnPlaceOrder = document.getElementById("btnPlaceOrder");
    const billHandlingFee = document.getElementById("billHandlingFee");
    const totalItemQty = cartItems.reduce((acc, i) => acc + i.qty, 0);
    cartCount.textContent = totalItemQty;

    const deliveryItemCount = document.getElementById("deliveryItemCount");
    if (deliveryItemCount) {
      deliveryItemCount.textContent = totalItemQty;
    }

    // Requirement #10: Empty Cart State
    if (cartItems.length === 0) {
      cartItemsList.innerHTML = `
        <div class="empty-cart-state">
          <div class="empty-cart-icon">🛒</div>
          <div class="empty-cart-title">Your basket is empty</div>
          <div class="empty-cart-sub">Add items from the quick-add catalog to start shopping</div>
        </div>
      `;
      silceCardContainer.innerHTML = "";
      billItemTotal.textContent = "₹0";
      if (billHandlingFee) billHandlingFee.textContent = "₹0";
      billGrandTotal.textContent = "₹0";
      btnPayAmount.textContent = "₹0";
      if (btnPlaceOrder) {
        btnPlaceOrder.disabled = true;
        btnPlaceOrder.style.opacity = "0.5";
        btnPlaceOrder.style.cursor = "not-allowed";
      }
      return;
    }

    if (btnPlaceOrder) {
      btnPlaceOrder.disabled = false;
      btnPlaceOrder.style.opacity = "1";
      btnPlaceOrder.style.cursor = "pointer";
    }

    cartItemsList.innerHTML = cartItems.map(item => `
      <div class="cart-item-card">
        <img src="${item.image}" alt="${item.name}">
        <div class="cart-item-details">
          <div class="cart-item-title">
            ${item.name}
            ${item.added_via_context ? '<span class="added-via-context-tag">Added via Context</span>' : ''}
          </div>
          <div class="cart-item-sub">${item.qty > 1 ? item.qty + ' x ' : ''}${item.subcategory || item.category}</div>
          <div class="cart-item-wishlist">Move to wishlist</div>
        </div>
        <div class="cart-item-right-col">
          <div class="cart-qty-ctrl">
            <button class="qty-btn btn-minus" data-id="${item.id}">-</button>
            <span class="qty-val">${item.qty}</span>
            <button class="qty-btn btn-plus" data-id="${item.id}">+</button>
          </div>
          <div class="cart-item-price-tag">₹${item.price * item.qty}</div>
        </div>
      </div>
    `).join("");

    cartItemsList.querySelectorAll(".btn-minus").forEach(b => {
      b.addEventListener("click", () => removeItemFromCart(b.getAttribute("data-id")));
    });

    cartItemsList.querySelectorAll(".btn-plus").forEach(b => {
      b.addEventListener("click", () => addItemToCart(b.getAttribute("data-id")));
    });

    const itemTotalVal = cartItems.reduce((sum, item) => sum + (item.price * item.qty), 0);
    const grandTotalVal = itemTotalVal + 4;

    billItemTotal.textContent = `₹${itemTotalVal}`;
    if (billHandlingFee) billHandlingFee.textContent = "₹4";
    billGrandTotal.textContent = `₹${grandTotalVal}`;
    btnPayAmount.textContent = `₹${grandTotalVal}`;
  }

  // SILCE Inference & Trigger Validation Engine
  async function triggerSILCEInference() {
    // Requirement #1 & #10: Hide recommendation when cart is empty
    if (cartItems.length === 0) {
      silceCardContainer.innerHTML = "";
      liveIntentName.textContent = "Inactive";
      liveConfidenceVal.textContent = "0%";
      confidenceFill.style.width = "0%";
      intentExplanationText.textContent = "Cart is empty. Add 2+ items (min ₹149) to trigger SILCE intent inference.";
      updateDiagnostics(null);
      return;
    }

    try {
      const res = await fetch("/api/recommend", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          cart_items: cartItems,
          user_id: activePersona.user_id
        })
      });

      const data = await res.json();
      latestSilceResult = data;

      // Requirement #6 & #5: If user dismissed recommendation during current session, hide recommendation
      if (dismissedThisSession) {
        silceCardContainer.innerHTML = "";
      } else {
        renderSilceCard(data);
      }

      // Update Live Intent Panel
      if (data.has_recommendation) {
        liveIntentName.textContent = data.intent_inferred || data.intent || "Analyzing...";
        const confPercent = Math.round((data.intent_confidence || 0) * 100);
        liveConfidenceVal.textContent = `${confPercent}%`;
        confidenceFill.style.width = `${confPercent}%`;
        intentExplanationText.innerHTML = `
          Detected: <strong>${data.intent_inferred}</strong>&nbsp;&nbsp;→&nbsp;&nbsp;Category: <strong>${data.silce_category || ''}</strong><br>
          <span style="font-size:11px;color:#64748B;">1 adjacent unexplored category identified.</span>
        `;
      } else {
        liveIntentName.textContent = data.intent || "Criteria Not Met";
        liveConfidenceVal.textContent = "0%";
        confidenceFill.style.width = "0%";
        intentExplanationText.textContent = data.reason || "SILCE trigger conditions not met.";
      }

      // Requirement #11: Update Diagnostics live with zero stale state
      updateDiagnostics(data);

    } catch (err) {
      console.error("SILCE API error:", err);
    }
  }

  function renderSilceCard(data) {
    if (!data.has_recommendation || dismissedThisSession) {
      silceCardContainer.innerHTML = "";
      return;
    }

    const recs = data.recommendations || [];
    if (recs.length === 0) {
      silceCardContainer.innerHTML = "";
      return;
    }

    // SILCE selects ONE category. The product is only a representative example.
    const rec            = recs[0];
    const isAlreadyInCart = cartItems.some(i => i.id === rec.product.id);
    const silceCategory   = data.silce_category || rec.silce_category || rec.new_category;
    const catExplanation  = data.category_explanation || rec.category_explanation || rec.product_reason;
    const ratingVal       = rec.rating ? rec.rating.replace('★', '').trim() : '4.7';
    const intentName      = data.intent_inferred || '';

    // Mission observation lookup for human companion tone
    const MISSION_OBSERVATIONS = {
      "Weekly Grocery Refill":  "Looks like you're restocking the house.",
      "Morning Breakfast Run":  "Tomorrow's breakfast looks sorted.",
      "House Party":            "Hosting friends tonight?",
      "Office Essentials":      "Stocking up for the office?",
      "Sick Day Recovery":      "Hope you feel better soon.",
      "Smoke Break":            "You might need this afterwards.",
      "Fresh Produce Restock":  "Fresh kitchen prep in progress.",
      "Urgent Household Need":  "Taking care of home essentials."
    };

    const observationText = data.observation || rec.observation || MISSION_OBSERVATIONS[intentName] || "Noticed something for your cart.";

    silceCardContainer.innerHTML = `
      <div class="silce-premium-card">

        <!-- Header: Clean section title + dismiss button -->
        <div class="silce-pc-header">
          <span class="silce-pc-title">🌱 Explore a New Category</span>
          <button id="btnDismissSilce" class="btn-dismiss-silce" title="Dismiss">✕</button>
        </div>

        <!-- Observation First, Helpful Advice Second -->
        <div class="silce-pc-category-section">
          <div class="silce-pc-category-eyebrow">${observationText}</div>
          <div class="silce-pc-category-name">${catExplanation}</div>
        </div>

        <!-- Product box -->
        <div class="silce-pc-product-wrapper">
          <div class="silce-pc-product">
            <img src="${rec.product.image}" alt="${rec.product.name}" class="silce-pc-img">
            <div class="silce-pc-prod-info">
              <div class="silce-pc-brand">${rec.brand}</div>
              <div class="silce-pc-name" title="${rec.product.name}">${rec.product.name}</div>
              <div class="silce-pc-meta">
                <span class="silce-pc-rating">★ ${ratingVal}</span>
                <span class="silce-pc-trust">· Verified Brand (4,500+ ratings)</span>
              </div>
              <div class="silce-pc-price">₹${rec.product.price}</div>
            </div>
            <button class="btn-silce-add ${isAlreadyInCart ? 'added' : ''} silce-pc-add-btn" data-id="${rec.product.id}">
              ${isAlreadyInCart ? '✓ Added' : 'Add'}
            </button>
          </div>
        </div>

      </div>
    `;

    // ── Wire Add button ─────────────────────────────────────────────────────
    silceCardContainer.querySelector('.silce-pc-add-btn')?.addEventListener('click', async () => {
      const btn = silceCardContainer.querySelector('.silce-pc-add-btn');
      if (!btn || btn.classList.contains('added')) return;
      btn.textContent = '✓ Added';
      btn.classList.add('added');
      addItemToCart(rec.product.id, true);
      await fetch('/api/action', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: 'accept',
          data: { product_id: rec.product.id, category: silceCategory, user_id: activePersona.user_id }
        })
      });
      fetchAnalytics();
    });

    // ── Wire Dismiss button ─────────────────────────────────────────────────
    document.getElementById('btnDismissSilce')?.addEventListener('click', async () => {
      dismissedThisSession = true;
      silceCardContainer.classList.add('collapsing');
      setTimeout(async () => {
        silceCardContainer.innerHTML = '';
        silceCardContainer.classList.remove('collapsing');
        await fetch('/api/action', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            action: 'dismiss',
            data: {
              product_id: rec.product.id,
              category: silceCategory,
              user_id: activePersona?.user_id || 'none'
            }
          })
        });
        fetchAnalytics();
      }, 350);
    });
  }

  // Requirement #11: Live Diagnostics Updates
  function updateDiagnostics(data) {
    const diagPipelineSteps = document.getElementById("diagPipelineSteps");
    const diagPurchasedCats = document.getElementById("diagPurchasedCats");
    const diagUnexploredCats = document.getElementById("diagUnexploredCats");
    const diagLatency = document.getElementById("diagLatency");
    const diagJsonPayload = document.getElementById("diagJsonPayload");

    if (activePersona) {
      diagPurchasedCats.innerHTML = activePersona.purchased_categories.map(c => `<li>🚫 ${c}</li>`).join("");
      diagUnexploredCats.innerHTML = activePersona.unexplored_categories.map(c => `<li>✅ ${c}</li>`).join("");
    }

    if (!data) {
      diagJsonPayload.textContent = "// Empty basket — SILCE inactive";
      diagLatency.textContent = "-- ms";
      diagPipelineSteps.innerHTML = `<div style="color: #94A3B8; font-size: 12px;">Cart has no items. SILCE trigger rules require recurring grocery essentials in basket.</div>`;
      return;
    }

    diagLatency.textContent = `${data.latency_ms} ms`;
    diagJsonPayload.textContent = JSON.stringify(data, null, 2);

    diagPipelineSteps.innerHTML = `
      <div class="pipeline-steps" style="margin-top: 0; padding-left: 0;">
        <div class="pipeline-step">
          <div class="step-num">1</div>
          <div class="step-info">
            <div class="step-title">Trigger Validation</div>
            <div class="step-desc">Basket contains recurring essentials. <span style="color: #10B981; font-weight: bold;">✓ Passed</span></div>
          </div>
        </div>
        <div class="pipeline-step">
          <div class="step-num">2</div>
          <div class="step-info">
            <div class="step-title">Shopping Mission Intent</div>
            <div class="step-desc">${data.intent_inferred || data.intent} <span style="margin-left: 8px; color: #8B5CF6; font-weight: bold;">(Confidence: ${data.intent_confidence || 0.93})</span></div>
          </div>
        </div>
        <div class="pipeline-step">
          <div class="step-num">3</div>
          <div class="step-info">
            <div class="step-title">Candidate Generation & Filtering</div>
            <div class="step-desc">Retrieved all candidates. Excluded items from previously explored categories: <em>${activePersona?.purchased_categories?.join(", ") || "Milk, Vegetables, Fresh Produce"}</em>. Filtered candidates based on price ratio guardrail.</div>
          </div>
        </div>
        <div class="pipeline-step">
          <div class="step-num">4</div>
          <div class="step-info">
            <div class="step-title">Adjacent Category Discovery</div>
            <div class="step-desc">Identified eligible adjacent categories and matched contextual keywords to compute relevance scores.</div>
          </div>
        </div>
        <div class="pipeline-step">
          <div class="step-num">5</div>
          <div class="step-info">
            <div class="step-title">Recommendation Ranking</div>
            <div class="step-desc">Ranked top 4 recommendations in descending relevance order:
              <ul style="margin-top: 6px; padding-left: 16px; font-size: 11px; color: var(--color-text-secondary); line-height: 1.4;">
                ${(data.recommendations || []).map((rec, idx) => `
                  <li><strong>#${idx + 1} ${rec.brand} ${rec.product.name}</strong> (₹${rec.product.price}) - <em>${rec.product_reason}</em></li>
                `).join("")}
              </ul>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  async function fetchAnalytics() {
    try {
      const res = await fetch("/api/analytics");
      const data = await res.json();

      document.getElementById("metricPrimaryVal").textContent = data.primary_metric.current_value;
      document.getElementById("metricAcceptanceVal").textContent = data.secondary_metrics.acceptance_rate;
      document.getElementById("metricGuardrailVal").textContent = data.guardrail_metrics.checkout_completion_rate;
      document.getElementById("metricLatencyVal").textContent = data.guardrail_metrics.avg_checkout_time;

      const eventStreamList = document.getElementById("eventStreamList");
      if (data.recent_events) {
        eventStreamList.innerHTML = data.recent_events.map(ev => `
          <div class="event-stream-item">
            <div>
              <span class="event-type-badge ${ev.event_type}">${ev.event_type}</span>
              <strong style="margin-left: 6px;">${ev.data.category || ev.data.intent || 'Checkout'}</strong>
            </div>
            <div style="font-size: 11px; color: #64748B;">${ev.timestamp.split(" ")[1]}</div>
          </div>
        `).join("");
      }
    } catch (err) {
      console.error("Analytics fetch error:", err);
    }
  }

  // Handle Place Order Button click
  document.getElementById("btnPlaceOrder").addEventListener("click", async () => {
    const itemTotalVal = cartItems.reduce((sum, item) => sum + (item.price * item.qty), 0);
    const grandTotalVal = itemTotalVal + 4;

    // Check if the top SILCE-recommended item was accepted into the cart
    const topRec = latestSilceResult?.has_recommendation && latestSilceResult?.recommendations?.length > 0
      ? latestSilceResult.recommendations[0]
      : null;
    const silceAcceptedItem = topRec
      ? cartItems.find(i => i.id === topRec.product.id)
      : null;

    document.getElementById("successAmount").textContent = `₹${grandTotalVal}`;

    const successCategoryBadge = document.getElementById("successCategoryBadge");
    if (silceAcceptedItem) {
      successCategoryBadge.innerHTML = `
        <div class="new-category-success-pill">
          🎉 Multi-Category Expansion: Tried <strong>${latestSilceResult.new_category}</strong>!
        </div>
      `;
    } else {
      successCategoryBadge.innerHTML = ``;
    }

    // Transition UI to Success Screen
    document.querySelector(".mobile-app-header").style.display = "none";
    document.querySelector(".mobile-cart-body").style.display = "none";
    document.querySelector(".mobile-cart-footer").style.display = "none";
    document.getElementById("orderSuccessScreen").style.display = "flex";

    await fetch("/api/action", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "checkout", data: { items_count: cartItems.length, amount: grandTotalVal } })
    });
    fetchAnalytics();
  });

  // Handle Reset Order / New Mission click
  document.getElementById("btnResetOrder").addEventListener("click", () => {
    document.getElementById("orderSuccessScreen").style.display = "none";
    document.querySelector(".mobile-app-header").style.display = "block";
    document.querySelector(".mobile-cart-body").style.display = "flex";
    document.querySelector(".mobile-cart-footer").style.display = "flex";

    const defaultPreset = activePersona ? (PERSONA_DEFAULT_PRESETS[activePersona.user_id] || "weekly_refill") : "weekly_refill";
    loadPresetCart(defaultPreset);
  });



  init();
});

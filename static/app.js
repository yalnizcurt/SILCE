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
    user_groceries_only: "weekly_refill",
    user_interview_prep: "breakfast_run",
    user_party_recovery: "produce_restock"
  };

  const MISSION_PRESETS = [
    {
      key: "weekly_refill",
      icon: "🛒",
      title: "Weekly Grocery Refill",
      desc: "Milk, Cucumber, Rice, Atta",
      items: ["prod_104", "prod_112", "prod_108", "prod_109"]
    },
    {
      key: "breakfast_run",
      icon: "🍳",
      title: "Morning Breakfast Run",
      desc: "Milk, Whole Wheat Bread, Eggs, Butter",
      items: ["prod_104", "prod_213", "prod_210", "prod_214"]
    },
    {
      key: "produce_restock",
      icon: "🥗",
      title: "Fresh Produce Restock",
      desc: "Tomato, Cucumber, Onion, Spinach",
      items: ["prod_113", "prod_112", "prod_114", "prod_115"]
    },
    {
      key: "house_party",
      icon: "🎉",
      title: "House Party",
      desc: "Soft Drinks, Chips, Ice Cream",
      items: ["prod_301", "prod_302", "prod_303"]
    },
    {
      key: "smoke_break",
      icon: "🚬",
      title: "Smoke Break",
      desc: "Cigarettes, Mint, Soft Drink",
      items: ["prod_401", "prod_402", "prod_301"]
    },
    {
      key: "office_essentials",
      icon: "💼",
      title: "Office Essentials",
      desc: "Coffee, Biscuits, Instant Noodles",
      items: ["prod_501", "prod_106", "prod_503"]
    },
    {
      key: "sick_recovery",
      icon: "🤒",
      title: "Sick Day Recovery",
      desc: "Crocin, ORS, Thermometer",
      items: ["prod_601", "prod_602", "prod_603"]
    },
    {
      key: "urgent_household",
      icon: "🚨",
      title: "Urgent Household Need",
      desc: "Garbage Bags, Floor Cleaner, Dishwash Liquid",
      items: ["prod_701", "prod_702", "prod_703"]
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

  let showAllPresets = false;

  function renderMissionPresets(activePresetKey) {
    const container = document.getElementById("missionPresetsContainer");
    const toggleBtn = document.getElementById("btnTogglePresets");
    if (!container) return;

    // Display first 4 initially, or all if showAllPresets is true
    const visiblePresets = showAllPresets ? MISSION_PRESETS : MISSION_PRESETS.slice(0, 4);

    container.innerHTML = visiblePresets.map(m => `
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

    if (toggleBtn) {
      toggleBtn.style.display = "block";
      toggleBtn.textContent = showAllPresets ? "Show Less Missions ▵" : "Show More Missions ▾";
    }
  }

  const btnTogglePresets = document.getElementById("btnTogglePresets");
  if (btnTogglePresets) {
    btnTogglePresets.addEventListener("click", () => {
      showAllPresets = !showAllPresets;
      const activeBtn = document.querySelector(".preset-btn.active");
      const activePresetKey = activeBtn ? activeBtn.getAttribute("data-preset") : "weekly_refill";
      renderMissionPresets(activePresetKey);
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
          Detected basket context: <strong>${data.intent_inferred}</strong>.<br>
          Surfaced 1 product from unexplored category: <strong>${data.new_category}</strong>.
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

    const prod = data.product;
    const isAlreadyInCart = cartItems.some(i => i.id === prod.id);

    silceCardContainer.innerHTML = `
      <div class="silce-card">
        <div class="silce-card-header">
          <div class="native-addon-title">Complete your cart</div>
          <div class="silce-card-actions">
            <button id="btnWhySilce" class="btn-why-silce">Why?</button>
            <button id="btnDismissSilce" class="btn-dismiss-silce" title="Dismiss suggestion">✕</button>
          </div>
        </div>
        <div class="silce-nudge">${data.nudge_text}</div>
        <div class="silce-prod-body">
          <img src="${prod.image}" class="silce-prod-img" alt="${prod.name}">
          <div class="silce-prod-info">
            <div class="silce-prod-name">${prod.name}</div>
            <div class="silce-prod-meta" style="font-size: 11px; color: #16A34A; margin-top: 2px; font-weight: 500;">✓ Trusted Brand &nbsp;✓ 4.6★+</div>
            <div class="silce-prod-price" style="margin-top: 4px;">₹${prod.price}</div>
          </div>
          <button id="btnAcceptSilce" class="btn-silce-add ${isAlreadyInCart ? 'added' : ''}">
            ${isAlreadyInCart ? '✓ Added' : 'Add to Basket'}
          </button>
        </div>
      </div>
    `;

    // Button Morphing + Single-Tap Add Action
    const btnAccept = document.getElementById("btnAcceptSilce");
    btnAccept.addEventListener("click", async () => {
      if (btnAccept.classList.contains("added")) return;

      btnAccept.textContent = "✓ Added";
      btnAccept.classList.add("added");

      addItemToCart(prod.id, true);

      await fetch("/api/action", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action: "accept",
          data: { product_id: prod.id, category: data.new_category, user_id: activePersona.user_id }
        })
      });
      fetchAnalytics();
    });

    // WhyBottomSheet Modal Handler
    document.getElementById("btnWhySilce").addEventListener("click", () => {
      const cartSubtotal = cartItems.reduce((sum, item) => sum + (item.price * item.qty), 0);
      const maxAllowed = Math.max(0.40 * cartSubtotal, 120).toFixed(0);

      document.getElementById("sheetIntentText").innerHTML = `Inferred <strong>${data.intent_inferred}</strong> intent from active basket.`;
      document.getElementById("sheetCategoryText").innerHTML = `Candidate SKU belongs to <strong>${data.new_category}</strong> (0 purchases in 90 days).`;
      document.getElementById("sheetPriceText").innerHTML = `Price <strong>&#8377;${prod.price}</strong> &le; 40% of subtotal (Max limit &#8377;${maxAllowed} for &#8377;${cartSubtotal} subtotal).`;

      if (whyBottomSheetModal) {
        whyBottomSheetModal.style.display = "flex";
      }
    });

    // Dismiss Collapse Animation Handler
    document.getElementById("btnDismissSilce").addEventListener("click", async () => {
      silceCardContainer.classList.add("collapsing");
      setTimeout(async () => {
        dismissedThisSession = true;
        silceCardContainer.innerHTML = "";
        silceCardContainer.classList.remove("collapsing");

        await fetch("/api/action", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            action: "dismiss",
            data: { product_id: prod.id, user_id: activePersona.user_id }
          })
        });
        fetchAnalytics();
      }, 300);
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
            <div class="step-desc">Basket contains recurring grocery essentials. <span style="color: #10B981; font-weight: bold;">✓ Passed</span></div>
          </div>
        </div>
        <div class="pipeline-step">
          <div class="step-num">2</div>
          <div class="step-info">
            <div class="step-title">Shopping Mission</div>
            <div class="step-desc">${data.intent_inferred || data.intent} <span style="margin-left: 8px; color: #8B5CF6; font-weight: bold;">(Confidence: ${data.intent_confidence || 0.93})</span></div>
          </div>
        </div>
        <div class="pipeline-step">
          <div class="step-num">3</div>
          <div class="step-info">
            <div class="step-title">Historical Category Analysis</div>
            <div class="step-desc">Previously explored: ${activePersona?.purchased_categories?.join(", ") || "Milk, Vegetables, Fresh Produce"}. Exclude those categories.</div>
          </div>
        </div>
        <div class="pipeline-step">
          <div class="step-num">4</div>
          <div class="step-info">
            <div class="step-title">Adjacent Category Discovery</div>
            <div class="step-desc">Evaluate relevant but under-explored grocery categories.</div>
          </div>
        </div>
        <div class="pipeline-step">
          <div class="step-num">5</div>
          <div class="step-info">
            <div class="step-title">Recommendation Selection</div>
            <div class="step-desc">Recommend: <strong>${data.product?.name || "Eggs"}</strong>. Reason: ${data.product_reason || "Frequently complements recurring grocery purchases."}</div>
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

    // Check if SILCE recommended item was accepted in cart
    const silceAcceptedItem = latestSilceResult?.has_recommendation ?
      cartItems.find(i => i.id === latestSilceResult.product.id) : null;

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

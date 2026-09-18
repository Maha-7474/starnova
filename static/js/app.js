"use strict";

class ApiError extends Error {
    constructor(message, status) {
        super(message);
        this.name = "ApiError";
        this.status = status;
    }
}

/** Request a same-origin JSON endpoint and turn safe API errors into UI errors. */
async function apiFetch(path, options = {}) {
    const headers = new Headers(options.headers || {});
    headers.set("Accept", "application/json");

    const requestOptions = { ...options };
    const isJsonBody = options.body
        && typeof options.body === "object"
        && !(options.body instanceof FormData)
        && !(options.body instanceof URLSearchParams)
        && !(options.body instanceof Blob);

    if (isJsonBody && !headers.has("Content-Type")) {
        headers.set("Content-Type", "application/json");
        requestOptions.body = JSON.stringify(options.body);
    }

    let response;
    try {
        response = await fetch(path, {
            ...requestOptions,
            headers,
            credentials: "same-origin",
        });
    } catch (error) {
        throw new ApiError("We couldn’t reach StarNova. Check your connection and try again.", 0);
    }

    let payload = null;
    try {
        payload = await response.json();
    } catch (error) {
        // A non-JSON failure is still handled below without exposing raw content.
    }

    if (!response.ok) {
        const message = payload && typeof payload.message === "string" && payload.message.trim()
            ? payload.message
            : "The service could not complete this request. Please try again.";
        throw new ApiError(message, response.status);
    }

    return payload;
}

let currentUser = null;
let activePostForApplication = null;
const elements = {};

function resetFiltersToDefault() {
    if (elements && elements.search) elements.search.value = "";
    if (elements && elements.type) elements.type.value = "";
    if (elements && elements.category) elements.category.value = "";
}

function initElements() {
    elements.form = document.querySelector("#filter-form");
    elements.search = document.querySelector("#search-input");
    elements.type = document.querySelector("#type-filter");
    elements.category = document.querySelector("#category-filter");
    elements.clear = document.querySelector("#clear-filters");
    elements.list = document.querySelector("#opportunity-list");
    elements.loading = document.querySelector("#loading-state");
    elements.empty = document.querySelector("#empty-state");
    elements.error = document.querySelector("#error-state");
    elements.errorMessage = document.querySelector("#error-message");
    elements.retry = document.querySelector("#retry-button");
    elements.summary = document.querySelector("#result-summary");
    elements.dialog = document.querySelector("#opportunity-dialog");
    elements.detail = document.querySelector("#detail-content");
    elements.closeDetail = document.querySelector("#close-detail");
    elements.navAuth = document.querySelector("#nav-auth-container");
    elements.authDialog = document.querySelector("#auth-dialog");
    elements.closeAuth = document.querySelector("#close-auth");
    elements.tabLogin = document.querySelector("#tab-login");
    elements.tabRegister = document.querySelector("#tab-register");
    elements.loginPanel = document.querySelector("#login-panel");
    elements.registerPanel = document.querySelector("#register-panel");
    elements.loginForm = document.querySelector("#login-form");
    elements.loginEmail = document.querySelector("#login-email");
    elements.loginPassword = document.querySelector("#login-password");
    elements.loginError = document.querySelector("#login-error");
    elements.switchToRegister = document.querySelector("#switch-to-register");
    elements.registerForm = document.querySelector("#register-form");
    elements.registerName = document.querySelector("#register-name");
    elements.registerEmail = document.querySelector("#register-email");
    elements.registerPassword = document.querySelector("#register-password");
    elements.registerConfirmPassword = document.querySelector("#register-confirm-password");
    elements.registerRoleApplicant = document.querySelector("#role-applicant");
    elements.registerError = document.querySelector("#register-error");
    elements.registerSuccess = document.querySelector("#register-success");
    elements.switchToLogin = document.querySelector("#switch-to-login");

    elements.appDialog = document.querySelector("#application-dialog");
    elements.closeApp = document.querySelector("#close-application");
    elements.appTitleDisplay = document.querySelector("#app-opportunity-title-display");
    elements.appError = document.querySelector("#application-error");
    elements.appForm = document.querySelector("#application-form");
    elements.appExperience = document.querySelector("#app-experience");
    elements.appPortfolio = document.querySelector("#app-portfolio");
    elements.appSubmitBtn = document.querySelector("#app-submit-btn");
    elements.appCancelBtn = document.querySelector("#app-cancel-btn");

    elements.myAppsSection = document.querySelector("#my-applications");
    elements.myAppsSummary = document.querySelector("#my-apps-summary");
    elements.myAppsLoading = document.querySelector("#my-apps-loading");
    elements.myAppsError = document.querySelector("#my-apps-error");
    elements.myAppsErrorMessage = document.querySelector("#my-apps-error-message");
    elements.myAppsRetry = document.querySelector("#my-apps-retry-button");
    elements.myAppsEmpty = document.querySelector("#my-apps-empty");
    elements.myAppsList = document.querySelector("#my-apps-list");

    elements.discoverySection = document.querySelector("#opportunities");
    elements.heroSection = document.querySelector(".hero");

    elements.organizerSection = document.querySelector("#organizer-dashboard");
    elements.organizerSummary = document.querySelector("#organizer-summary");
    elements.organizerLoading = document.querySelector("#organizer-loading");
    elements.organizerError = document.querySelector("#organizer-error");
    elements.organizerErrorMessage = document.querySelector("#organizer-error-message");
    elements.organizerRetry = document.querySelector("#organizer-retry-button");
    elements.organizerEmpty = document.querySelector("#organizer-empty");
    elements.organizerList = document.querySelector("#organizer-list");
    elements.createOppBtn = document.querySelector("#create-opportunity-btn");
    elements.createFirstOppBtn = document.querySelector("#create-first-opportunity-btn");

    elements.oppFormDialog = document.querySelector("#opportunity-form-dialog");
    elements.oppFormTitle = document.querySelector("#opp-form-title");
    elements.oppFormError = document.querySelector("#opportunity-form-error");
    elements.oppForm = document.querySelector("#opportunity-form");
    elements.postTitle = document.querySelector("#post-title");
    elements.postType = document.querySelector("#post-type");
    elements.postCategory = document.querySelector("#post-category");
    elements.postEventDate = document.querySelector("#post-event-date");
    elements.postStartTime = document.querySelector("#post-start-time");
    elements.postEndTime = document.querySelector("#post-end-time");
    elements.postVenue = document.querySelector("#post-venue");
    elements.postDescription = document.querySelector("#post-description");
    elements.postSubmitBtn = document.querySelector("#post-submit-btn");
    elements.postCancelBtn = document.querySelector("#post-cancel-btn");
    elements.closeOppForm = document.querySelector("#close-opp-form");

    elements.applicantsDialog = document.querySelector("#applicants-dialog");
    elements.applicantsTitle = document.querySelector("#applicants-title");
    elements.applicantsSummary = document.querySelector("#applicants-summary");
    elements.applicantsLoading = document.querySelector("#applicants-loading");
    elements.applicantsError = document.querySelector("#applicants-error");
    elements.applicantsErrorMessage = document.querySelector("#applicants-error-message");
    elements.applicantsEmpty = document.querySelector("#applicants-empty");
    elements.applicantsList = document.querySelector("#applicants-list");
    elements.closeApplicants = document.querySelector("#close-applicants");
}

function formatDate(value) {
    if (!value) return "Date to be announced";
    const date = new Date(`${value}T00:00:00`);
    return Number.isNaN(date.getTime())
        ? value
        : new Intl.DateTimeFormat("en-IN", { day: "numeric", month: "short", year: "numeric" }).format(date);
}

function formatTime(value) {
    if (!value) return "Time to be announced";
    const parts = value.split(":");
    if (parts.length < 2) return value;
    const time = new Date();
    time.setHours(Number(parts[0]), Number(parts[1]), 0, 0);
    return Number.isNaN(time.getTime())
        ? value
        : new Intl.DateTimeFormat("en-IN", { hour: "numeric", minute: "2-digit" }).format(time);
}

function formatSchedule(post) {
    const date = formatDate(post.event_date);
    return !post.start_time || !post.end_time
        ? date
        : `${date} · ${formatTime(post.start_time)}–${formatTime(post.end_time)}`;
}

function setVisibility(element, isVisible) {
    element.hidden = !isVisible;
}

function setPageState(state, message = "") {
    setVisibility(elements.loading, state === "loading");
    setVisibility(elements.empty, state === "empty");
    setVisibility(elements.error, state === "error");
    elements.list.hidden = state !== "ready";
    elements.list.setAttribute("aria-busy", String(state === "loading"));
    if (state !== "ready") {
        elements.list.replaceChildren();
    }
    if (state === "error") {
        elements.errorMessage.textContent = message;
    } else {
        elements.errorMessage.textContent = "";
    }
}

function appendMetaItem(container, label, value) {
    const row = document.createElement("div");
    row.className = "meta-item";
    const labelElement = document.createElement("span");
    labelElement.className = "meta-label";
    labelElement.textContent = label;
    const valueElement = document.createElement("span");
    valueElement.textContent = value;
    row.append(labelElement, valueElement);
    container.append(row);
}

function createOpportunityCard(post) {
    const card = document.createElement("article");
    card.className = "opportunity-card";

    const topline = document.createElement("div");
    topline.className = "card-topline";
    const type = document.createElement("span");
    type.className = "badge";
    type.textContent = post.opportunity_type;
    const category = document.createElement("span");
    category.className = "category";
    category.textContent = post.category;
    topline.append(type, category);

    const title = document.createElement("h3");
    title.textContent = post.title;
    const meta = document.createElement("div");
    meta.className = "meta";
    appendMetaItem(meta, "When", formatSchedule(post));
    appendMetaItem(meta, "Where", post.venue || "Venue to be announced");

    const description = document.createElement("p");
    description.className = "description";
    description.textContent = post.description || "No description provided.";
    if (!post.description) description.classList.add("is-empty");

    const view = document.createElement("a");
    view.className = "view-link";
    view.href = `?post=${encodeURIComponent(post.id)}#opportunities`;
    view.textContent = "View opportunity →";
    view.addEventListener("click", (event) => {
        if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
        event.preventDefault();
        openOpportunity(post.id);
    });

    card.append(topline, title, meta, description, view);
    return card;
}

function renderPosts(posts) {
    elements.list.replaceChildren();
    elements.summary.textContent = `${posts.length} ${posts.length === 1 ? "opportunity" : "opportunities"} found`;
    if (posts.length === 0) {
        setPageState("empty");
        return;
    }
    const fragment = document.createDocumentFragment();
    posts.forEach((post) => fragment.append(createOpportunityCard(post)));
    elements.list.append(fragment);
    setPageState("ready");
}

function currentFilters() {
    return {
        q: elements.search.value.trim(),
        type: elements.type.value,
        category: elements.category.value,
    };
}

function buildPostListUrl() {
    const params = new URLSearchParams();
    Object.entries(currentFilters()).forEach(([key, value]) => {
        if (value) params.set(key, value);
    });
    const queryString = params.toString();
    return queryString ? `/api/posts?${queryString}` : "/api/posts";
}

async function loadPosts() {
    elements.summary.textContent = "";
    setPageState("loading");
    try {
        const payload = await apiFetch(buildPostListUrl());
        renderPosts(Array.isArray(payload?.posts) ? payload.posts : []);
    } catch (error) {
        elements.list.replaceChildren();
        elements.summary.textContent = "";
        setPageState("error", error instanceof ApiError ? error.message : "Something unexpected went wrong.");
    }
}

function clearDetailUrl() {
    const url = new URL(window.location.href);
    url.searchParams.delete("post");
    history.replaceState({}, "", `${url.pathname}${url.search}${url.hash}`);
}

function renderDetail(post) {
    elements.detail.replaceChildren();
    const type = document.createElement("span");
    type.className = "badge";
    type.textContent = `${post.opportunity_type} · ${post.category}`;
    const title = document.createElement("h2");
    title.id = "detail-title";
    title.textContent = post.title;
    const meta = document.createElement("div");
    meta.className = "meta";
    appendMetaItem(meta, "When", formatSchedule(post));
    appendMetaItem(meta, "Where", post.venue || "Venue to be announced");
    const description = document.createElement("p");
    description.className = "description";
    description.textContent = post.description || "No description provided.";
    if (!post.description) description.classList.add("is-empty");
    elements.detail.append(type, title, meta, description);

    // Phase 6C: Opportunity Apply actions
    const actions = document.createElement("div");
    actions.className = "detail-actions";

    if (currentUser && currentUser.role === "user") {
        const applyBtn = document.createElement("button");
        applyBtn.id = "detail-apply-btn";
        applyBtn.className = "button button-primary";
        applyBtn.type = "button";
        applyBtn.textContent = "Apply Now";
        applyBtn.addEventListener("click", () => {
            openApplicationModal(post);
        });
        actions.append(applyBtn);
        elements.detail.append(actions);
    } else if (!currentUser) {
        const promptBox = document.createElement("div");
        promptBox.className = "detail-login-prompt";
        const promptText = document.createElement("p");
        promptText.textContent = "Want to apply for this opportunity?";
        const loginApplyBtn = document.createElement("button");
        loginApplyBtn.id = "detail-login-apply-btn";
        loginApplyBtn.className = "button button-primary button-sm";
        loginApplyBtn.type = "button";
        loginApplyBtn.textContent = "Login to apply";
        loginApplyBtn.addEventListener("click", () => {
            closeOpportunity();
            openAuthModal("login");
        });
        promptBox.append(promptText, loginApplyBtn);
        actions.append(promptBox);
        elements.detail.append(actions);
    }
}

function renderDetailError(message) {
    elements.detail.replaceChildren();
    const panel = document.createElement("div");
    panel.className = "state-panel state-error";
    const heading = document.createElement("h3");
    heading.textContent = "We couldn’t load this opportunity";
    const copy = document.createElement("p");
    copy.textContent = message;
    panel.append(heading, copy);
    elements.detail.append(panel);
}

async function openOpportunity(id, updateUrl = true) {
    if (updateUrl) {
        const url = new URL(window.location.href);
        url.searchParams.set("post", id);
        history.pushState({}, "", `${url.pathname}${url.search}${url.hash}`);
    }

    elements.detail.replaceChildren();
    const loading = document.createElement("div");
    loading.className = "state-panel";
    loading.textContent = "Loading opportunity details…";
    elements.detail.append(loading);
    if (!elements.dialog.open) elements.dialog.showModal();

    try {
        const payload = await apiFetch(`/api/posts/${encodeURIComponent(id)}`);
        if (!payload?.post) throw new ApiError("This opportunity could not be found.", 404);
        renderDetail(payload.post);
    } catch (error) {
        renderDetailError(error instanceof ApiError ? error.message : "Something unexpected went wrong.");
    }
}

function closeOpportunity() {
    if (elements.dialog.open) elements.dialog.close();
    clearDetailUrl();
}

function isValidUrl(urlString) {
    if (!urlString || typeof urlString !== "string") return false;
    try {
        const parsed = new URL(urlString.trim());
        return parsed.protocol === "http:" || parsed.protocol === "https:";
    } catch (e) {
        return false;
    }
}

function clearApplicationError() {
    if (elements.appError) {
        elements.appError.hidden = true;
        elements.appError.textContent = "";
    }
}

function showApplicationError(message) {
    if (elements.appError) {
        elements.appError.textContent = message;
        elements.appError.hidden = false;
    }
}

function openApplicationModal(post) {
    activePostForApplication = post;
    if (elements.appTitleDisplay) {
        elements.appTitleDisplay.textContent = `Applying for: ${post.title}`;
    }
    if (elements.appExperience) elements.appExperience.value = "";
    if (elements.appPortfolio) elements.appPortfolio.value = "";
    clearApplicationError();
    if (elements.appSubmitBtn) {
        elements.appSubmitBtn.disabled = false;
        elements.appSubmitBtn.textContent = "Submit Application";
    }
    if (elements.appDialog && !elements.appDialog.open) {
        elements.appDialog.showModal();
    }
}

function closeApplicationModal() {
    if (elements.appDialog && elements.appDialog.open) {
        elements.appDialog.close();
    }
    activePostForApplication = null;
    clearApplicationError();
}

async function handleApplicationSubmit(event) {
    event.preventDefault();
    clearApplicationError();

    if (!activePostForApplication) {
        showApplicationError("No opportunity selected.");
        return;
    }

    const experience = elements.appExperience ? elements.appExperience.value.trim() : "";
    const portfolioUrl = elements.appPortfolio ? elements.appPortfolio.value.trim() : "";

    if (!experience) {
        showApplicationError("Experience is required.");
        return;
    }

    if (portfolioUrl && !isValidUrl(portfolioUrl)) {
        showApplicationError("Portfolio URL must be a valid HTTP or HTTPS URL.");
        return;
    }

    if (elements.appSubmitBtn) {
        elements.appSubmitBtn.disabled = true;
        elements.appSubmitBtn.textContent = "Submitting…";
    }

    try {
        const body = {
            experience: experience,
            portfolio_url: portfolioUrl || null,
        };
        await apiFetch(`/api/posts/${encodeURIComponent(activePostForApplication.id)}/apply`, {
            method: "POST",
            body,
        });

        closeApplicationModal();
        closeOpportunity();
        window.location.hash = "#my-applications";
        handleRoute();
    } catch (error) {
        if (elements.appSubmitBtn) {
            elements.appSubmitBtn.disabled = false;
            elements.appSubmitBtn.textContent = "Submit Application";
        }
        showApplicationError(error instanceof ApiError ? error.message : "Failed to submit application.");
    }
}

function setMyAppsPageState(state, message = "") {
    if (elements.myAppsLoading) setVisibility(elements.myAppsLoading, state === "loading");
    if (elements.myAppsEmpty) setVisibility(elements.myAppsEmpty, state === "empty");
    if (elements.myAppsError) setVisibility(elements.myAppsError, state === "error");
    if (elements.myAppsList) {
        elements.myAppsList.hidden = state !== "ready";
        elements.myAppsList.setAttribute("aria-busy", String(state === "loading"));
        if (state !== "ready") {
            elements.myAppsList.replaceChildren();
        }
    }
    if (state === "error" && elements.myAppsErrorMessage) {
        elements.myAppsErrorMessage.textContent = message;
    } else if (elements.myAppsErrorMessage) {
        elements.myAppsErrorMessage.textContent = "";
    }
}

function getStatusBadgeClass(status) {
    switch (status) {
        case "Pending":
            return "status-pending";
        case "Under Review":
            return "status-under-review";
        case "Shortlisted":
            return "status-shortlisted";
        case "Selected":
            return "status-selected";
        case "Rejected":
            return "status-rejected";
        default:
            return "status-pending";
    }
}

function renderMyApplications(applications) {
    if (!elements.myAppsList) return;
    elements.myAppsList.replaceChildren();
    if (elements.myAppsSummary) {
        elements.myAppsSummary.textContent = `${applications.length} ${applications.length === 1 ? "application" : "applications"} submitted`;
    }

    if (applications.length === 0) {
        setMyAppsPageState("empty");
        return;
    }

    const fragment = document.createDocumentFragment();
    applications.forEach((app) => {
        const card = document.createElement("article");
        card.className = "application-card";

        const header = document.createElement("div");
        header.className = "app-card-header";

        const titleGroup = document.createElement("div");
        const title = document.createElement("h3");
        title.textContent = app.title || "Opportunity";

        const typeCategory = document.createElement("span");
        typeCategory.className = "category";
        typeCategory.textContent = `${app.opportunity_type || ""} · ${app.category || ""}`;
        titleGroup.append(title, typeCategory);

        const statusBadge = document.createElement("span");
        statusBadge.className = `status-badge ${getStatusBadgeClass(app.status)}`;
        statusBadge.textContent = app.status || "Pending";

        header.append(titleGroup, statusBadge);

        const body = document.createElement("div");
        body.className = "app-card-body";

        appendMetaItem(body, "When", formatDate(app.event_date));
        appendMetaItem(body, "Where", app.venue || "Venue to be announced");

        if (app.applied_at) {
            const rawAppliedDate = typeof app.applied_at === "string" ? app.applied_at.split("T")[0] : app.applied_at;
            appendMetaItem(body, "Applied", formatDate(rawAppliedDate));
        }

        if (app.portfolio_url) {
            const row = document.createElement("div");
            row.className = "meta-item";
            const label = document.createElement("span");
            label.className = "meta-label";
            label.textContent = "Portfolio";
            const link = document.createElement("a");
            link.className = "portfolio-link";
            link.href = app.portfolio_url;
            link.target = "_blank";
            link.rel = "noopener noreferrer";
            link.textContent = app.portfolio_url;
            row.append(label, link);
            body.append(row);
        }

        if (app.experience) {
            const expBox = document.createElement("div");
            expBox.className = "experience-box";
            expBox.textContent = app.experience;
            body.append(expBox);
        }

        card.append(header, body);
        fragment.append(card);
    });

    elements.myAppsList.append(fragment);
    setMyAppsPageState("ready");
}

async function loadMyApplications() {
    if (!currentUser || currentUser.role !== "user") return;
    if (elements.myAppsSummary) elements.myAppsSummary.textContent = "";
    setMyAppsPageState("loading");

    try {
        const payload = await apiFetch("/api/my-applications");
        const apps = Array.isArray(payload?.applications) ? payload.applications : [];
        renderMyApplications(apps);
    } catch (error) {
        if (elements.myAppsList) elements.myAppsList.replaceChildren();
        if (elements.myAppsSummary) elements.myAppsSummary.textContent = "";
        setMyAppsPageState("error", error instanceof ApiError ? error.message : "Something unexpected went wrong.");
    }
}

let editingPostId = null;
let activePostForApplicants = null;

function setOrganizerPageState(state, message = "") {
    if (elements.organizerLoading) setVisibility(elements.organizerLoading, state === "loading");
    if (elements.organizerEmpty) setVisibility(elements.organizerEmpty, state === "empty");
    if (elements.organizerError) setVisibility(elements.organizerError, state === "error");
    if (elements.organizerList) {
        elements.organizerList.hidden = state !== "ready";
        elements.organizerList.setAttribute("aria-busy", String(state === "loading"));
        if (state !== "ready") {
            elements.organizerList.replaceChildren();
        }
    }
    if (state === "error" && elements.organizerErrorMessage) {
        elements.organizerErrorMessage.textContent = message;
    }
}

async function loadOrganizerDashboard() {
    if (!currentUser || currentUser.role !== "organizer") return;
    if (elements.organizerSummary) elements.organizerSummary.textContent = "";
    setOrganizerPageState("loading");

    try {
        const payload = await apiFetch("/api/posts");
        const allPosts = Array.isArray(payload?.posts) ? payload.posts : [];
        const myPosts = allPosts.filter((p) => p.organizer_id === currentUser.id);
        renderOrganizerPosts(myPosts);
    } catch (error) {
        if (elements.organizerList) elements.organizerList.replaceChildren();
        if (elements.organizerSummary) elements.organizerSummary.textContent = "";
        setOrganizerPageState("error", error instanceof ApiError ? error.message : "Something unexpected went wrong.");
    }
}

function createOrganizerCard(post) {
    const card = document.createElement("article");
    card.className = "opportunity-card organizer-card";

    const topline = document.createElement("div");
    topline.className = "card-topline";
    const type = document.createElement("span");
    type.className = "badge";
    type.textContent = post.opportunity_type;
    const category = document.createElement("span");
    category.className = "category";
    category.textContent = post.category;
    topline.append(type, category);

    const title = document.createElement("h3");
    title.textContent = post.title;

    const meta = document.createElement("div");
    meta.className = "meta";
    appendMetaItem(meta, "When", formatSchedule(post));
    appendMetaItem(meta, "Where", post.venue || "Venue to be announced");

    const description = document.createElement("p");
    description.className = "description";
    description.textContent = post.description || "No description provided.";
    if (!post.description) description.classList.add("is-empty");

    const actions = document.createElement("div");
    actions.className = "organizer-card-actions";

    const viewBtn = document.createElement("button");
    viewBtn.className = "button button-secondary";
    viewBtn.type = "button";
    viewBtn.textContent = "View";
    viewBtn.addEventListener("click", () => openOpportunity(post.id));

    const editBtn = document.createElement("button");
    editBtn.className = "button button-secondary";
    editBtn.type = "button";
    editBtn.textContent = "Edit";
    editBtn.addEventListener("click", () => openEditOpportunityModal(post));

    const applicantsBtn = document.createElement("button");
    applicantsBtn.className = "button button-primary";
    applicantsBtn.type = "button";
    applicantsBtn.textContent = "View Applicants";
    applicantsBtn.addEventListener("click", () => openApplicantsModal(post));

    const deleteBtn = document.createElement("button");
    deleteBtn.className = "button button-danger";
    deleteBtn.type = "button";
    deleteBtn.textContent = "Delete";
    deleteBtn.addEventListener("click", () => handleDeleteOpportunity(post));

    actions.append(viewBtn, editBtn, applicantsBtn, deleteBtn);
    card.append(topline, title, meta, description, actions);
    return card;
}

function renderOrganizerPosts(posts) {
    if (!elements.organizerList) return;
    elements.organizerList.replaceChildren();
    if (elements.organizerSummary) {
        elements.organizerSummary.textContent = `${posts.length} ${posts.length === 1 ? "opportunity" : "opportunities"} posted`;
    }

    if (posts.length === 0) {
        setOrganizerPageState("empty");
        return;
    }

    const fragment = document.createDocumentFragment();
    posts.forEach((post) => fragment.append(createOrganizerCard(post)));
    elements.organizerList.append(fragment);
    setOrganizerPageState("ready");
}

function clearOppFormError() {
    if (elements.oppFormError) {
        elements.oppFormError.hidden = true;
        elements.oppFormError.textContent = "";
    }
}

function showOppFormError(message) {
    if (elements.oppFormError) {
        elements.oppFormError.textContent = message;
        elements.oppFormError.hidden = false;
    }
}

function openCreateOpportunityModal() {
    editingPostId = null;
    if (elements.oppFormTitle) elements.oppFormTitle.textContent = "Create Opportunity";
    if (elements.oppForm) elements.oppForm.reset();
    clearOppFormError();
    if (elements.postSubmitBtn) {
        elements.postSubmitBtn.disabled = false;
        elements.postSubmitBtn.textContent = "Create Opportunity";
    }
    if (elements.oppFormDialog && !elements.oppFormDialog.open) {
        elements.oppFormDialog.showModal();
    }
}

function openEditOpportunityModal(post) {
    editingPostId = post.id;
    if (elements.oppFormTitle) elements.oppFormTitle.textContent = "Edit Opportunity";
    if (elements.postTitle) elements.postTitle.value = post.title || "";
    if (elements.postType) elements.postType.value = post.opportunity_type || "audition";
    if (elements.postCategory) elements.postCategory.value = post.category || "acting";
    if (elements.postEventDate) elements.postEventDate.value = post.event_date || "";
    if (elements.postStartTime) elements.postStartTime.value = post.start_time ? post.start_time.substring(0, 5) : "";
    if (elements.postEndTime) elements.postEndTime.value = post.end_time ? post.end_time.substring(0, 5) : "";
    if (elements.postVenue) elements.postVenue.value = post.venue || "";
    if (elements.postDescription) elements.postDescription.value = post.description || "";

    clearOppFormError();
    if (elements.postSubmitBtn) {
        elements.postSubmitBtn.disabled = false;
        elements.postSubmitBtn.textContent = "Save Changes";
    }
    if (elements.oppFormDialog && !elements.oppFormDialog.open) {
        elements.oppFormDialog.showModal();
    }
}

function closeOpportunityFormModal() {
    if (elements.oppFormDialog && elements.oppFormDialog.open) {
        elements.oppFormDialog.close();
    }
    editingPostId = null;
    clearOppFormError();
}

async function handleOpportunityFormSubmit(event) {
    event.preventDefault();
    clearOppFormError();

    const title = elements.postTitle ? elements.postTitle.value.trim() : "";
    const opportunity_type = elements.postType ? elements.postType.value : "audition";
    const category = elements.postCategory ? elements.postCategory.value : "acting";
    const event_date = elements.postEventDate ? elements.postEventDate.value : "";
    const start_time = elements.postStartTime && elements.postStartTime.value ? elements.postStartTime.value : null;
    const end_time = elements.postEndTime && elements.postEndTime.value ? elements.postEndTime.value : null;
    const venue = elements.postVenue ? elements.postVenue.value.trim() : "";
    const description = elements.postDescription ? elements.postDescription.value.trim() : "";

    if (!title) { showOppFormError("Title is required."); return; }
    if (!event_date) { showOppFormError("Event date is required."); return; }
    if (!venue) { showOppFormError("Venue is required."); return; }
    if ((start_time && !end_time) || (!start_time && end_time)) {
        showOppFormError("Start time and end time must be provided together.");
        return;
    }
    if (start_time && end_time && end_time <= start_time) {
        showOppFormError("End time must be later than start time.");
        return;
    }

    if (elements.postSubmitBtn) {
        elements.postSubmitBtn.disabled = true;
        elements.postSubmitBtn.textContent = "Saving…";
    }

    const body = {
        title,
        opportunity_type,
        category,
        event_date,
        start_time,
        end_time,
        venue,
        description: description || null,
    };

    try {
        if (editingPostId) {
            await apiFetch(`/api/posts/${editingPostId}`, { method: "PUT", body });
        } else {
            await apiFetch("/api/posts", { method: "POST", body });
        }
        closeOpportunityFormModal();
        loadOrganizerDashboard();
        loadPosts();
    } catch (error) {
        if (elements.postSubmitBtn) {
            elements.postSubmitBtn.disabled = false;
            elements.postSubmitBtn.textContent = editingPostId ? "Save Changes" : "Create Opportunity";
        }
        showOppFormError(error instanceof ApiError ? error.message : "Failed to save opportunity.");
    }
}

async function handleDeleteOpportunity(post) {
    if (!confirm(`Are you sure you want to delete "${post.title}"?`)) return;
    try {
        await apiFetch(`/api/posts/${post.id}`, { method: "DELETE" });
        loadOrganizerDashboard();
        loadPosts();
    } catch (error) {
        alert(error instanceof ApiError ? error.message : "Failed to delete opportunity.");
    }
}

function clearApplicantsError() {
    if (elements.applicantsError) {
        elements.applicantsError.hidden = true;
        elements.applicantsError.textContent = "";
    }
}

function showApplicantsError(message) {
    if (elements.applicantsError) {
        elements.applicantsError.textContent = message;
        elements.applicantsError.hidden = false;
    }
}

function setApplicantsPageState(state, message = "") {
    if (elements.applicantsLoading) setVisibility(elements.applicantsLoading, state === "loading");
    if (elements.applicantsEmpty) setVisibility(elements.applicantsEmpty, state === "empty");
    if (elements.applicantsError) setVisibility(elements.applicantsError, state === "error");
    if (elements.applicantsList) {
        elements.applicantsList.hidden = state !== "ready";
        if (state !== "ready") elements.applicantsList.replaceChildren();
    }
    if (state === "error" && elements.applicantsErrorMessage) {
        elements.applicantsErrorMessage.textContent = message;
    }
}

async function openApplicantsModal(post) {
    activePostForApplicants = post;
    if (elements.applicantsTitle) elements.applicantsTitle.textContent = `Applicants: ${post.title}`;
    if (elements.applicantsSummary) elements.applicantsSummary.textContent = "";
    clearApplicantsError();

    if (elements.applicantsDialog && !elements.applicantsDialog.open) {
        elements.applicantsDialog.showModal();
    }
    setApplicantsPageState("loading");

    try {
        const payload = await apiFetch(`/api/posts/${post.id}/applications`);
        const applications = Array.isArray(payload?.applications) ? payload.applications : [];
        renderApplicantsList(applications);
    } catch (error) {
        setApplicantsPageState("error", error instanceof ApiError ? error.message : "Failed to load applicants.");
    }
}

function closeApplicantsModal() {
    if (elements.applicantsDialog && elements.applicantsDialog.open) {
        elements.applicantsDialog.close();
    }
    activePostForApplicants = null;
    clearApplicantsError();
}

function renderApplicantsList(applications) {
    if (!elements.applicantsList) return;
    elements.applicantsList.replaceChildren();

    if (elements.applicantsSummary) {
        elements.applicantsSummary.textContent = `${applications.length} ${applications.length === 1 ? "applicant" : "applicants"} total`;
    }

    if (applications.length === 0) {
        setApplicantsPageState("empty");
        return;
    }

    const fragment = document.createDocumentFragment();
    applications.forEach((app) => {
        const card = document.createElement("div");
        card.className = "applicant-review-card";

        const header = document.createElement("div");
        header.className = "applicant-header";

        const info = document.createElement("div");
        info.className = "applicant-info";
        const name = document.createElement("strong");
        name.textContent = app.applicant_name || "Applicant";
        const email = document.createElement("p");
        email.textContent = app.applicant_email || "";
        info.append(name, email);

        const statusSelect = document.createElement("select");
        statusSelect.className = "app-status-select";
        ["Pending", "Under Review", "Shortlisted", "Selected", "Rejected"].forEach((statusOpt) => {
            const opt = document.createElement("option");
            opt.value = statusOpt;
            opt.textContent = statusOpt;
            if (statusOpt === app.status) opt.selected = true;
            statusSelect.append(opt);
        });

        statusSelect.addEventListener("change", async (e) => {
            const newStatus = e.target.value;
            const previousStatus = app.status;
            try {
                await apiFetch(`/api/applications/${app.id}/status`, {
                    method: "PUT",
                    body: { status: newStatus },
                });
                app.status = newStatus;
            } catch (err) {
                e.target.value = previousStatus;
                showApplicantsError(err instanceof ApiError ? err.message : "Failed to update status.");
            }
        });

        header.append(info, statusSelect);
        card.append(header);

        if (app.applied_at) {
            const rawAppliedDate = typeof app.applied_at === "string" ? app.applied_at.split("T")[0] : app.applied_at;
            appendMetaItem(card, "Applied", formatDate(rawAppliedDate));
        }

        if (app.portfolio_url) {
            const row = document.createElement("div");
            row.className = "meta-item";
            const label = document.createElement("span");
            label.className = "meta-label";
            label.textContent = "Portfolio";
            const link = document.createElement("a");
            link.className = "portfolio-link";
            link.href = app.portfolio_url;
            link.target = "_blank";
            link.rel = "noopener noreferrer";
            link.textContent = app.portfolio_url;
            row.append(label, link);
            card.append(row);
        }

        if (app.experience) {
            const expBox = document.createElement("div");
            expBox.className = "experience-box";
            expBox.textContent = app.experience;
            card.append(expBox);
        }

        fragment.append(card);
    });

    elements.applicantsList.append(fragment);
    setApplicantsPageState("ready");
}

function handleRoute() {
    const hash = window.location.hash;
    if (hash === "#my-applications") {
        if (currentUser && currentUser.role === "user") {
            if (elements.heroSection) elements.heroSection.hidden = true;
            if (elements.discoverySection) elements.discoverySection.hidden = true;
            if (elements.myAppsSection) elements.myAppsSection.hidden = false;
            if (elements.organizerSection) elements.organizerSection.hidden = true;
            loadMyApplications();
        } else {
            window.location.hash = "";
            showHomeView();
        }
    } else if (hash === "#organizer-dashboard") {
        if (currentUser && currentUser.role === "organizer") {
            if (elements.heroSection) elements.heroSection.hidden = true;
            if (elements.discoverySection) elements.discoverySection.hidden = true;
            if (elements.myAppsSection) elements.myAppsSection.hidden = true;
            if (elements.organizerSection) elements.organizerSection.hidden = false;
            loadOrganizerDashboard();
        } else {
            window.location.hash = "";
            showHomeView();
        }
    } else {
        showHomeView();
    }
}

function showHomeView() {
    if (elements.heroSection) elements.heroSection.hidden = false;
    if (elements.discoverySection) elements.discoverySection.hidden = false;
    if (elements.myAppsSection) elements.myAppsSection.hidden = true;
    if (elements.organizerSection) elements.organizerSection.hidden = true;
}

function updateNavigation() {
    const container = elements.navAuth || document.querySelector("#nav-auth-container");
    if (!container) return;
    container.replaceChildren();

    if (!currentUser) {
        // Public navigation
        const loginBtn = document.createElement("button");
        loginBtn.className = "nav-link nav-btn";
        loginBtn.type = "button";
        loginBtn.id = "nav-login-btn";
        loginBtn.textContent = "Login";
        loginBtn.addEventListener("click", () => openAuthModal("login"));

        const signUpBtn = document.createElement("button");
        signUpBtn.className = "button button-primary button-sm";
        signUpBtn.type = "button";
        signUpBtn.id = "nav-signup-btn";
        signUpBtn.textContent = "Sign Up";
        signUpBtn.addEventListener("click", () => openAuthModal("register"));

        container.append(loginBtn, signUpBtn);
    } else if (currentUser.role === "user") {
        // Applicant navigation
        const myAppsLink = document.createElement("a");
        myAppsLink.className = "nav-link";
        myAppsLink.href = "#my-applications";
        myAppsLink.textContent = "My Applications";

        const roleBadge = document.createElement("span");
        roleBadge.className = "user-role-badge badge-applicant";
        roleBadge.textContent = "Applicant";

        const logoutBtn = document.createElement("button");
        logoutBtn.className = "nav-link nav-btn";
        logoutBtn.type = "button";
        logoutBtn.id = "nav-logout-btn";
        logoutBtn.textContent = "Logout";
        logoutBtn.addEventListener("click", handleLogout);

        container.append(myAppsLink, roleBadge, logoutBtn);
    } else if (currentUser.role === "organizer") {
        // Organizer navigation
        const dashboardLink = document.createElement("a");
        dashboardLink.className = "nav-link";
        dashboardLink.href = "#organizer-dashboard";
        dashboardLink.textContent = "Organizer Dashboard";

        const roleBadge = document.createElement("span");
        roleBadge.className = "user-role-badge badge-organizer";
        roleBadge.textContent = "Organizer";

        const logoutBtn = document.createElement("button");
        logoutBtn.className = "nav-link nav-btn";
        logoutBtn.type = "button";
        logoutBtn.id = "nav-logout-btn";
        logoutBtn.textContent = "Logout";
        logoutBtn.addEventListener("click", handleLogout);

        container.append(dashboardLink, roleBadge, logoutBtn);
    }
}

async function checkSession() {
    try {
        const payload = await apiFetch("/api/me");
        if (payload && payload.user) {
            currentUser = payload.user;
        } else {
            currentUser = null;
        }
    } catch (error) {
        currentUser = null;
    }
    updateNavigation();
    handleRoute();
}

function clearAuthBanners() {
    if (elements.loginError) {
        elements.loginError.hidden = true;
        elements.loginError.textContent = "";
    }
    if (elements.registerError) {
        elements.registerError.hidden = true;
        elements.registerError.textContent = "";
    }
    if (elements.registerSuccess) {
        elements.registerSuccess.hidden = true;
        elements.registerSuccess.textContent = "";
    }
}

function switchAuthTab(tab) {
    clearAuthBanners();
    if (tab === "login") {
        elements.tabLogin.classList.add("is-active");
        elements.tabLogin.setAttribute("aria-selected", "true");
        elements.tabRegister.classList.remove("is-active");
        elements.tabRegister.setAttribute("aria-selected", "false");
        elements.loginPanel.hidden = false;
        elements.registerPanel.hidden = true;
        elements.loginEmail.focus();
    } else {
        elements.tabRegister.classList.add("is-active");
        elements.tabRegister.setAttribute("aria-selected", "true");
        elements.tabLogin.classList.remove("is-active");
        elements.tabLogin.setAttribute("aria-selected", "false");
        elements.registerPanel.hidden = false;
        elements.loginPanel.hidden = true;
        elements.registerName.focus();
    }
}

function openAuthModal(tab = "login") {
    switchAuthTab(tab);
    if (elements.authDialog && !elements.authDialog.open) {
        elements.authDialog.showModal();
    }
}

function closeAuthModal() {
    if (elements.authDialog && elements.authDialog.open) {
        elements.authDialog.close();
    }
    clearAuthBanners();
}

function showAuthError(panel, message) {
    clearAuthBanners();
    if (panel === "login" && elements.loginError) {
        elements.loginError.textContent = message;
        elements.loginError.hidden = false;
    } else if (panel === "register" && elements.registerError) {
        elements.registerError.textContent = message;
        elements.registerError.hidden = false;
    }
}

function showAuthSuccess(panel, message) {
    clearAuthBanners();
    if (panel === "register" && elements.registerSuccess) {
        elements.registerSuccess.textContent = message;
        elements.registerSuccess.hidden = false;
    }
}

async function handleLogin(event) {
    event.preventDefault();
    clearAuthBanners();

    const email = elements.loginEmail.value.trim();
    const password = elements.loginPassword.value;

    if (!email || !password) {
        showAuthError("login", "Please enter your email and password.");
        return;
    }

    try {
        const payload = await apiFetch("/api/auth/login", {
            method: "POST",
            body: { email, password },
        });
        currentUser = payload.user;
        updateNavigation();
        closeAuthModal();
        elements.loginForm.reset();
        handleRoute();
    } catch (error) {
        showAuthError("login", error instanceof ApiError ? error.message : "Invalid email or password.");
    }
}

async function handleRegister(event) {
    event.preventDefault();
    clearAuthBanners();

    const name = elements.registerName.value.trim();
    const email = elements.registerEmail.value.trim();
    const password = elements.registerPassword.value;
    const confirmPassword = elements.registerConfirmPassword.value;
    const role = elements.registerRoleApplicant.checked ? "user" : "organizer";

    if (!name) {
        showAuthError("register", "Name is required.");
        return;
    }
    if (!email) {
        showAuthError("register", "A valid email is required.");
        return;
    }
    if (!password || password.length < 8) {
        showAuthError("register", "Password must be at least 8 characters long.");
        return;
    }
    if (password !== confirmPassword) {
        showAuthError("register", "Passwords do not match.");
        return;
    }

    try {
        await apiFetch("/api/auth/register", {
            method: "POST",
            body: { name, email, password, role },
        });
        showAuthSuccess("register", "Registration successful! Redirecting to login…");
        elements.registerForm.reset();
        setTimeout(() => {
            switchAuthTab("login");
            elements.loginEmail.value = email;
            elements.loginPassword.focus();
        }, 1200);
    } catch (error) {
        showAuthError("register", error instanceof ApiError ? error.message : "Registration failed. Please try again.");
    }
}

async function handleLogout() {
    try {
        await apiFetch("/api/auth/logout", { method: "POST" });
    } catch (error) {
        // Clear local state even if logout request fails
    }
    currentUser = null;
    updateNavigation();
    if (window.location.hash === "#my-applications") {
        window.location.hash = "";
    }
    handleRoute();
}

function setupEventListeners() {
    if (elements.form) {
        elements.form.addEventListener("submit", (event) => {
            event.preventDefault();
            loadPosts();
        });
    }
    [elements.type, elements.category].forEach((filter) => {
        if (filter) filter.addEventListener("change", loadPosts);
    });
    if (elements.clear) {
        elements.clear.addEventListener("click", () => {
            resetFiltersToDefault();
            loadPosts();
        });
    }
    if (elements.retry) elements.retry.addEventListener("click", loadPosts);
    if (elements.closeDetail) elements.closeDetail.addEventListener("click", closeOpportunity);
    if (elements.dialog) elements.dialog.addEventListener("close", clearDetailUrl);
    window.addEventListener("popstate", () => {
        const postId = new URLSearchParams(window.location.search).get("post");
        if (postId) openOpportunity(postId, false);
        else if (elements.dialog && elements.dialog.open) elements.dialog.close();
    });

    if (elements.tabLogin) elements.tabLogin.addEventListener("click", () => switchAuthTab("login"));
    if (elements.tabRegister) elements.tabRegister.addEventListener("click", () => switchAuthTab("register"));
    if (elements.switchToRegister) elements.switchToRegister.addEventListener("click", () => switchAuthTab("register"));
    if (elements.switchToLogin) elements.switchToLogin.addEventListener("click", () => switchAuthTab("login"));
    if (elements.closeAuth) elements.closeAuth.addEventListener("click", closeAuthModal);
    if (elements.loginForm) elements.loginForm.addEventListener("submit", handleLogin);
    if (elements.registerForm) elements.registerForm.addEventListener("submit", handleRegister);

    if (elements.closeApp) elements.closeApp.addEventListener("click", closeApplicationModal);
    if (elements.appCancelBtn) elements.appCancelBtn.addEventListener("click", closeApplicationModal);
    if (elements.appForm) elements.appForm.addEventListener("submit", handleApplicationSubmit);
    if (elements.myAppsRetry) elements.myAppsRetry.addEventListener("click", loadMyApplications);
    if (elements.appDialog) elements.appDialog.addEventListener("close", clearApplicationError);

    if (elements.createOppBtn) elements.createOppBtn.addEventListener("click", openCreateOpportunityModal);
    if (elements.createFirstOppBtn) elements.createFirstOppBtn.addEventListener("click", openCreateOpportunityModal);
    if (elements.organizerRetry) elements.organizerRetry.addEventListener("click", loadOrganizerDashboard);
    if (elements.closeOppForm) elements.closeOppForm.addEventListener("click", closeOpportunityFormModal);
    if (elements.postCancelBtn) elements.postCancelBtn.addEventListener("click", closeOpportunityFormModal);
    if (elements.oppForm) elements.oppForm.addEventListener("submit", handleOpportunityFormSubmit);
    if (elements.oppFormDialog) elements.oppFormDialog.addEventListener("close", clearOppFormError);
    if (elements.closeApplicants) elements.closeApplicants.addEventListener("click", closeApplicantsModal);
    if (elements.applicantsDialog) elements.applicantsDialog.addEventListener("close", clearApplicantsError);

    window.addEventListener("hashchange", handleRoute);

    document.querySelectorAll('.brand, a[href="/"], a[href="#opportunities"]').forEach((link) => {
        link.addEventListener("click", () => {
            if (window.location.hash === "#my-applications" || window.location.hash === "#organizer-dashboard") {
                window.location.hash = "";
                showHomeView();
            }
        });
    });
}

document.addEventListener("DOMContentLoaded", () => {
    initElements();
    setupEventListeners();
    resetFiltersToDefault();
    checkSession();
    loadPosts();
    const postId = new URLSearchParams(window.location.search).get("post");
    if (postId) openOpportunity(postId, false);
});

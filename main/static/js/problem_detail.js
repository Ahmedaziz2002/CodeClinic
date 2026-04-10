(function () {
    const root = document.querySelector("[data-problem-detail]");
    if (!root) {
        return;
    }

    const humanSolutionsList = document.getElementById("human-solutions-list");
    const humanSolutionForm = root.querySelector("[data-human-solution-form]");
    const humanSolutionStatus = root.querySelector("[data-human-solution-status]");
    const emptyState = root.querySelector("[data-empty-human-solutions]");
    const modal = document.getElementById("solution-modal");
    const modalBody = document.getElementById("modal-solution-body");
    const modalClose = document.querySelector("[data-close-solution-modal]");
    const isOwner = root.dataset.isOwner === "true";
    const activeUsersList = root.querySelector("[data-active-users-list]");
    const activeUserCount = root.querySelector("[data-active-user-count]");
    const humanCount = root.querySelector("[data-human-count]");
    const liveStatus = root.querySelector("[data-live-status]");
    const liveText = root.querySelector("[data-live-text]");
    const liveDot = root.querySelector("[data-live-dot]");
    const mentionTargets = () => root.querySelectorAll("[data-mention-target]");

    const decodeUnicodeEscapes = (value) =>
        value.replace(/\\u([0-9a-fA-F]{4})/g, (_, code) => String.fromCharCode(parseInt(code, 16)));

    const decodeRaw = (value) =>
        decodeUnicodeEscapes(value)
            .replace(/\\n/g, "\n")
            .replace(/\\r/g, "\r")
            .replace(/\\t/g, "\t")
            .replace(/\\"/g, '"')
            .replace(/\\'/g, "'");

    const copyToClipboard = async (text, button) => {
        if (!text) {
            return;
        }
        try {
            await navigator.clipboard.writeText(decodeRaw(text));
            if (button) {
                const original = button.textContent;
                button.textContent = "Copied";
                button.disabled = true;
                setTimeout(() => {
                    button.textContent = original;
                    button.disabled = false;
                }, 1400);
            }
        } catch (error) {
            console.error("Copy failed", error);
        }
    };

    const bindCopyButtons = (scope) => {
        scope.querySelectorAll("[data-copy-raw]").forEach((button) => {
            if (button.dataset.bound === "true") {
                return;
            }
            button.dataset.bound = "true";
            button.addEventListener("click", () => copyToClipboard(button.dataset.copyRaw, button));
        });
    };

    const renderMessageBodies = (scope) => {
        scope.querySelectorAll("[data-message-content]").forEach((container) => {
            if (container.dataset.rendered === "true") {
                return;
            }
            container.dataset.rendered = "true";
            const raw = decodeRaw(container.dataset.raw || "");
            const parts = raw.split(/```/);
            const fragment = document.createDocumentFragment();

            parts.forEach((part, index) => {
                if (!part) {
                    return;
                }
                if (index % 2 === 1) {
                    let code = part;
                    let lang = "";
                    const newlineIndex = part.indexOf("\n");
                    if (newlineIndex !== -1) {
                        const maybeLang = part.slice(0, newlineIndex).trim();
                        if (maybeLang && maybeLang.length < 20 && !maybeLang.includes(" ")) {
                            lang = maybeLang;
                            code = part.slice(newlineIndex + 1);
                        }
                    }
                    const card = document.createElement("div");
                    card.className = "rounded-2xl border border-cyan-400/30 bg-slate-950/80 p-3 shadow-lg shadow-cyan-500/10";
                    const header = document.createElement("div");
                    header.className = "flex items-center justify-between";
                    const label = document.createElement("span");
                    label.className = "text-[0.65rem] font-semibold uppercase tracking-[0.2em] text-cyan-200";
                    label.textContent = lang ? `Code (${lang})` : "Code";
                    const copyButton = document.createElement("button");
                    copyButton.type = "button";
                    copyButton.className =
                        "cc-copy-button rounded-full border border-cyan-300/30 px-3 py-1 text-[0.65rem] font-semibold uppercase tracking-[0.15em] text-cyan-100 hover:border-cyan-300/60";
                    copyButton.dataset.copyRaw = code.trim();
                    copyButton.textContent = "Copy";
                    header.append(label, copyButton);
                    const pre = document.createElement("pre");
                    pre.className = "mt-3 max-h-64 overflow-auto rounded-xl bg-slate-950/90 p-3 text-xs text-cyan-100";
                    pre.textContent = code.trim();
                    card.append(header, pre);
                    fragment.append(card);
                } else {
                    const block = document.createElement("p");
                    block.className = "whitespace-pre-wrap break-words text-sm leading-6 text-slate-200";
                    block.textContent = part.trim();
                    fragment.append(block);
                }
            });

            if (!fragment.childNodes.length) {
                const fallback = document.createElement("p");
                fallback.className = "whitespace-pre-wrap break-words text-sm leading-6 text-slate-200";
                fallback.textContent = raw.trim();
                fragment.append(fallback);
            }

            container.innerHTML = "";
            container.append(fragment);
            bindCopyButtons(container);
        });
    };

    const getCookie = (name) => {
        const cookies = document.cookie ? document.cookie.split(";") : [];
        for (const rawCookie of cookies) {
            const cookie = rawCookie.trim();
            if (cookie.startsWith(`${name}=`)) {
                return decodeURIComponent(cookie.slice(name.length + 1));
            }
        }
        return null;
    };

    const bindVoteButtons = (scope) => {
        scope.querySelectorAll("[data-vote-type]").forEach((button) => {
            if (button.dataset.bound === "true") {
                return;
            }
            button.dataset.bound = "true";
            button.addEventListener("click", async () => {
                const solutionId = button.dataset.solutionId;
                const voteType = button.dataset.voteType;
                const response = await fetch(`/vote/${solutionId}/${voteType}/`, {
                    method: "POST",
                    headers: {
                        "X-CSRFToken": getCookie("csrftoken"),
                        "X-Requested-With": "XMLHttpRequest",
                    },
                });
                if (!response.ok) {
                    return;
                }
                const data = await response.json();
                document.getElementById(`upvotes-${solutionId}`).innerText = data.upvotes;
                document.getElementById(`downvotes-${solutionId}`).innerText = data.downvotes;
            });
        });
    };

    const bindModalTriggers = (scope) => {
        scope.querySelectorAll(".solution-modal-trigger").forEach((button) => {
            if (button.dataset.bound === "true") {
                return;
            }
            button.dataset.bound = "true";
            button.addEventListener("click", () => {
                const solutionId = button.dataset.solutionId;
                const solutionCard = document.getElementById(`solution-${solutionId}`);
                if (!solutionCard) {
                    return;
                }
                modalBody.innerHTML = solutionCard.innerHTML;
                renderMessageBodies(modalBody);
                bindCopyButtons(modalBody);
                bindVoteButtons(modalBody);
                modal.classList.remove("hidden");
            });
        });
    };

    const bindCardInteractions = (scope) => {
        bindVoteButtons(scope);
        bindModalTriggers(scope);
        renderMessageBodies(scope);
        bindCopyButtons(scope);
    };

    const insertMention = (username) => {
        const target = document.activeElement?.matches("[data-mention-target]")
            ? document.activeElement
            : mentionTargets()[0];
        if (!target) {
            return;
        }
        const mention = `@${username} `;
        const start = target.selectionStart ?? target.value.length;
        const end = target.selectionEnd ?? target.value.length;
        target.value = `${target.value.slice(0, start)}${mention}${target.value.slice(end)}`;
        target.focus();
        const nextCursor = start + mention.length;
        target.setSelectionRange(nextCursor, nextCursor);
    };

    const renderActiveUsers = (users) => {
        if (!activeUsersList || !activeUserCount) {
            return;
        }
        const uniqueUsers = Array.from(new Set(users.filter(Boolean)));
        activeUserCount.textContent = uniqueUsers.length;
        if (!uniqueUsers.length) {
            activeUsersList.innerHTML = '<p class="text-sm text-slate-500">No one else is active in this thread yet.</p>';
            return;
        }
        activeUsersList.innerHTML = uniqueUsers
            .map(
                (username) =>
                    `<button type="button" class="rounded-full border border-cyan-400/30 px-3 py-2 text-sm text-cyan-300 hover:bg-cyan-400/10" data-mention-username="${username}">@${username}</button>`
            )
            .join("");
        activeUsersList.querySelectorAll("[data-mention-username]").forEach((button) => {
            button.addEventListener("click", () => insertMention(button.dataset.mentionUsername));
        });
    };

    bindCardInteractions(document);
    renderMessageBodies(document);
    bindCopyButtons(document);
    renderActiveUsers(Array.from(activeUsersList?.querySelectorAll("[data-mention-username]") || []).map((button) => button.dataset.mentionUsername));

    if (modalClose) {
        modalClose.addEventListener("click", () => {
            modal.classList.add("hidden");
        });
    }

    window.addEventListener("click", (event) => {
        if (event.target === modal) {
            modal.classList.add("hidden");
        }
    });

    const updateHumanCount = () => {
        if (!humanCount) {
            return;
        }
        const count = humanSolutionsList ? humanSolutionsList.querySelectorAll("[data-solution-card]").length : 0;
        humanCount.textContent = count;
    };

    const insertSolutionCard = ({ html, solutionId }) => {
        if (!html || !humanSolutionsList) {
            return;
        }
        if (solutionId && document.getElementById(`solution-${solutionId}`)) {
            return;
        }
        if (emptyState) {
            emptyState.remove();
        }
        const wrapper = document.createElement("div");
        wrapper.innerHTML = html.trim();
        const card = wrapper.firstElementChild;
        if (!card) {
            return;
        }
        if (solutionId && !card.id) {
            card.id = `solution-${solutionId}`;
        }
        if (isOwner) {
            const metaRow = card.querySelector(".solution-modal-trigger")?.parentElement;
            if (metaRow && !metaRow.querySelector("form")) {
                const acceptForm = document.createElement("form");
                acceptForm.method = "POST";
                acceptForm.action = `/solution/${solutionId}/accept/`;
                acceptForm.className = "inline-flex";
                acceptForm.innerHTML = `<input type="hidden" name="csrfmiddlewaretoken" value="${getCookie("csrftoken") || ""}"><button type="submit" class="rounded-full border border-amber-400/40 px-3 py-2 text-xs font-semibold uppercase tracking-[0.15em] text-amber-300 hover:bg-amber-400/10">Accept</button>`;
                metaRow.prepend(acceptForm);
            }
        }
        humanSolutionsList.prepend(card);
        bindCardInteractions(card);
        updateHumanCount();
    };

    if (humanSolutionForm) {
        humanSolutionForm.addEventListener("submit", async (event) => {
            event.preventDefault();
            humanSolutionStatus.textContent = "Sharing your contribution...";

            const response = await fetch(root.dataset.solutionEndpoint, {
                method: "POST",
                headers: {
                    "X-CSRFToken": getCookie("csrftoken"),
                    "X-Requested-With": "XMLHttpRequest",
                },
                body: new FormData(humanSolutionForm),
            });

            const data = await response.json().catch(() => ({ error: "Could not share your contribution." }));
            if (!response.ok) {
                humanSolutionStatus.textContent = data.error || "Could not share your contribution.";
                return;
            }

            humanSolutionForm.reset();
            if (data.html_auth) {
                insertSolutionCard({ html: data.html_auth, solutionId: data.solution_id });
            } else if (data.html) {
                insertSolutionCard({ html: data.html, solutionId: data.solution_id });
            }
            humanSolutionStatus.textContent = "Contribution shared. It will appear instantly for everyone viewing this page.";
        });
    }

    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    let socket = null;
    let reconnectAttempts = 0;
    let reconnectTimer = null;

    const connectSocket = () => {
        if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) {
            return;
        }
        socket = new WebSocket(`${protocol}://${window.location.host}${root.dataset.wsPath}`);

        socket.addEventListener("message", (event) => {
            if (liveStatus) {
                liveStatus.dataset.liveState = "online";
                liveStatus.classList.remove("border-amber-400/40", "bg-amber-400/10", "text-amber-200");
                liveStatus.classList.add("border-emerald-400/30", "bg-emerald-500/10", "text-emerald-200");
            }
            if (liveText) {
                liveText.textContent = "Live";
            }
            if (liveDot) {
                liveDot.classList.remove("bg-amber-300", "shadow-[0_0_12px_rgba(251,191,36,0.7)]");
                liveDot.classList.add("bg-emerald-300", "shadow-[0_0_12px_rgba(52,211,153,0.7)]");
            }
            const data = JSON.parse(event.data);
            if (data.type === "presence.updated") {
                renderActiveUsers(data.active_users || []);
                return;
            }
            if (data.type !== "solution.created") {
                return;
            }

        insertSolutionCard({ html: data.html, solutionId: data.solution_id });
    });

        socket.addEventListener("close", () => {
            if (liveStatus) {
                liveStatus.dataset.liveState = "offline";
                liveStatus.classList.remove("border-emerald-400/30", "bg-emerald-500/10", "text-emerald-200");
                liveStatus.classList.add("border-amber-400/40", "bg-amber-400/10", "text-amber-200");
            }
            if (liveText) {
                liveText.textContent = "Offline";
            }
            if (liveDot) {
                liveDot.classList.remove("bg-emerald-300", "shadow-[0_0_12px_rgba(52,211,153,0.7)]");
                liveDot.classList.add("bg-amber-300", "shadow-[0_0_12px_rgba(251,191,36,0.7)]");
            }
            if (humanSolutionStatus && !humanSolutionStatus.textContent) {
                humanSolutionStatus.textContent = "Live updates are temporarily offline. Refresh the page if you need the latest answers.";
            }
            if (reconnectTimer) {
                return;
            }
            reconnectAttempts += 1;
            const delay = Math.min(8000, 500 * reconnectAttempts);
            reconnectTimer = setTimeout(() => {
                reconnectTimer = null;
                connectSocket();
            }, delay);
        });

        socket.addEventListener("open", () => {
            reconnectAttempts = 0;
            if (liveStatus) {
                liveStatus.dataset.liveState = "online";
                liveStatus.classList.remove("border-amber-400/40", "bg-amber-400/10", "text-amber-200");
                liveStatus.classList.add("border-emerald-400/30", "bg-emerald-500/10", "text-emerald-200");
            }
            if (liveText) {
                liveText.textContent = "Live";
            }
            if (liveDot) {
                liveDot.classList.remove("bg-amber-300", "shadow-[0_0_12px_rgba(251,191,36,0.7)]");
                liveDot.classList.add("bg-emerald-300", "shadow-[0_0_12px_rgba(52,211,153,0.7)]");
            }
        });
    };

    connectSocket();

    document.addEventListener("visibilitychange", () => {
        if (document.visibilityState === "visible") {
            connectSocket();
        }
    });
})();

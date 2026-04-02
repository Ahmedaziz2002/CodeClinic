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
    const mentionTargets = () => root.querySelectorAll("[data-mention-target]");

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
                bindVoteButtons(modalBody);
                modal.classList.remove("hidden");
            });
        });
    };

    const bindCardInteractions = (scope) => {
        bindVoteButtons(scope);
        bindModalTriggers(scope);
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
        activeUserCount.textContent = users.length;
        if (!users.length) {
            activeUsersList.innerHTML = '<p class="text-sm text-slate-500">No one else is active in this thread yet.</p>';
            return;
        }
        activeUsersList.innerHTML = users
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

            if (!response.ok) {
                const data = await response.json().catch(() => ({ error: "Could not share your contribution." }));
                humanSolutionStatus.textContent = data.error || "Could not share your contribution.";
                return;
            }

            humanSolutionForm.reset();
            humanSolutionStatus.textContent = "Contribution shared. It will appear instantly for everyone viewing this page.";
        });
    }

    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    const socket = new WebSocket(`${protocol}://${window.location.host}${root.dataset.wsPath}`);

    socket.addEventListener("message", (event) => {
        const data = JSON.parse(event.data);
        if (data.type === "presence.updated") {
            renderActiveUsers(data.active_users || []);
            return;
        }
        if (data.type !== "solution.created") {
            return;
        }

        if (emptyState) {
            emptyState.remove();
        }

        const wrapper = document.createElement("div");
        wrapper.innerHTML = data.html.trim();
        const card = wrapper.firstElementChild;
        if (!card) {
            return;
        }
        if (isOwner) {
            const metaRow = card.querySelector(".solution-modal-trigger")?.parentElement;
            if (metaRow) {
                const acceptForm = document.createElement("form");
                acceptForm.method = "POST";
                acceptForm.action = `/solution/${data.solution_id}/accept/`;
                acceptForm.className = "inline-flex";
                acceptForm.innerHTML = `<input type="hidden" name="csrfmiddlewaretoken" value="${getCookie("csrftoken") || ""}"><button type="submit" class="rounded-full border border-amber-400/40 px-3 py-2 text-xs font-semibold uppercase tracking-[0.15em] text-amber-300 hover:bg-amber-400/10">Accept</button>`;
                metaRow.prepend(acceptForm);
            }
        }
        humanSolutionsList.prepend(card);
        bindCardInteractions(card);
    });

    socket.addEventListener("close", () => {
        if (humanSolutionStatus && !humanSolutionStatus.textContent) {
            humanSolutionStatus.textContent = "Live updates are temporarily offline. Refresh the page if you need the latest answers.";
        }
    });
})();

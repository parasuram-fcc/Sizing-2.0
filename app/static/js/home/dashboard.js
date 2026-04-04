/* =============================================
   dashboard.js — Home / Dashboard page logic

   Jinja2 values are passed via hidden <input> elements
   in the template (ids: adminUser, currentUserCode,
   isFccProject, projRef, currentQuote, username, randomData).
   ============================================= */

/* =================== GLOBAL STATE =================== */
let adminUser = '';
let current_user_code = '';
let isFccUser = false;

let projectsearchType = 'customer';
let itemsearchType = 'tagNo';
let debounceTimer;
let currentRequestId = 0;

document.addEventListener('DOMContentLoaded', function () {
    adminUser        = document.getElementById('adminUser').value;
    current_user_code = document.getElementById('currentUserCode').value;
    isFccUser        = document.getElementById('isFccProject').value === 'true';
    window.PROJ_REF      = document.getElementById('projRef').value;
    window.CURRENT_QUOTE = document.getElementById('currentQuote').value;
});


/* =================== UTILITIES =================== */
// getCurrentIds() is defined in common/header.js (loaded before this file).

function formatDateTime(time) {
    const dateParts   = time.split(' ');
    const day         = dateParts[1];
    const month       = dateParts[2];
    const year        = dateParts[3];
    const t           = dateParts[4];
    const monthNames  = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
    const monthNumber = (monthNames.indexOf(month.substring(0, 3)) + 1).toString().padStart(2, '0');
    return `${year}-${monthNumber}-${day} ${t}`;
}


/* =================== SEARCH =================== */

function toggleSearchType() {
    const dropdown = document.getElementById("search_dropdown");
    dropdown.style.display = dropdown.style.display === "block" ? "none" : "block";
}

function toggleSearchTypeItem() {
    const dropdown = document.getElementById("search_dropdown_item");
    dropdown.style.display = dropdown.style.display === "block" ? "none" : "block";
}

function selectType(type, label) {
    projectsearchType = type;
    document.getElementById("search_type_label").innerText = label;
    document.getElementById("search_dropdown").style.display = "none";
    document.getElementById("search_input").focus();
}

function selectTypeItem(type, label) {
    itemsearchType = type;
    document.getElementById("search_type_label_item").innerText = label;
    document.getElementById("search_dropdown_item").style.display = "none";
    document.getElementById("search_input_item").focus();
}

function liveSearch(row_type) {
    clearTimeout(debounceTimer);

    const project_value = document.getElementById("search_input").value.trim();
    const item_value    = document.getElementById("search_input_item").value.trim();

    let value, searchType;
    if (row_type === 'project') {
        value      = project_value;
        searchType = projectsearchType;
    } else if (row_type === 'item') {
        value      = item_value;
        searchType = itemsearchType;
    }

    debounceTimer = setTimeout(() => {
        const requestId = ++currentRequestId;

        let url = (row_type === 'project') ? '/home' : window.location.pathname;
        url += `?type=${row_type}&search_type=${searchType}&search_value=${value}`;

        fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } })
            .then(res => (row_type === 'project') ? res.text() : res.json())
            .then(data => {
                if (requestId !== currentRequestId) return;
                if (row_type === 'project') {
                    $(".test").colResizable({ disable: true });
                    document.getElementById("projectlist").innerHTML = data;
                } else if (row_type === 'item') {
                    updateItemsList(data.items);
                }
            });
    }, 300);
}


/* =================== ITEMS =================== */

function updateItemsList(items) {
    const tbody = document.getElementById("itemsTableBody");
    tbody.innerHTML = "";

    items.forEach(item => {
        let row = '';

        if (isFccUser) {
            row = `
            <tr class="item-row" data-itemid="${item.itemId}" style="cursor:pointer">
                <td class="table2_item pdl-4">${item.itemNo}</td>
                <td class="table2_alt pdl-4">${item.itemalt}</td>
                <td class="table2_tag pdl-4">${item.tagNo}</td>
                <td class="table2_series pdl-4">${item.series}</td>
                <td class="table2_item pdl-4">${item.sizes}</td>
                <td class="table2_model pdl-4">${item.models}</td>
                <td class="table2_type pdl-4">${item.type}</td>
                <td class="table2_rating pdl-4">${item.rating}</td>
                <td class="table2_material pdl-4">${item.material}</td>
                <td class="table2_align pdl-4">${item.unit}</td>
                <td class="table2_series pdl-4">${item.qty}</td>
                <td class="table2_align pdl-4">${item.totalprice}</td>
                <td class="table2_type pdl-4">${item.cur_status}</td>
                <td class="table2_series pdl-4">${item.revision}</td>
                <td class="table2_alt revisionpopup"
                    data-action="item-revision"
                    data-toggle="modal"
                    data-target="#revisionModal"
                    onclick="passRevision(${item.revision}, ${item.itemId}, ${item.draft_status})">
                    <i class="fa-solid fa-eye"></i>
                </td>
                <td class="table2_print">
                    <a href="#" data-page="generate-csv-item" class="nav-dynamic">
                        <i class="fa-solid fa-print"></i>
                    </a>
                </td>
            </tr>`;
        } else {
            row = `
            <tr class="item-row" data-itemid="${item.itemId}" style="cursor:pointer">
                <td class="table2_item pdl-4">${item.itemNo}</td>
                <td class="table2_alt pdl-4">${item.itemalt}</td>
                <td class="table2_tag pdl-4">${item.tagNo}</td>
                <td class="table2_series pdl-4">${item.series}</td>
                <td class="table2_item pdl-4">${item.sizes}</td>
                <td class="table2_model pdl-4">${item.models}</td>
                <td class="table2_type pdl-4">${item.type}</td>
                <td class="table2_rating pdl-4">${item.rating}</td>
                <td class="table2_material pdl-4">${item.material}</td>
                <td class="table2_align pdl-4">${item.unit}</td>
                <td class="table2_series pdl-4">${item.qty}</td>
                <td class="table2_align pdl-4">${item.totalprice}</td>
                <td class="table2_print">
                    <a href="#" data-page="generate-csv-item" class="nav-dynamic">
                        <i class="fa-solid fa-print"></i>
                    </a>
                </td>
            </tr>`;
        }

        tbody.insertAdjacentHTML("beforeend", row);
    });

    attachItemRowHandlers();
}

function selectItemRow(itemId) {
    document.querySelectorAll(".item-row").forEach(row => {
        row.classList.remove("selected-row-item");
        if (row.dataset.itemid == itemId) {
            row.classList.add("selected-row-item");
        }
    });
}

function attachItemRowHandlers() {
    document.querySelectorAll(".item-row").forEach(row => {
        row.addEventListener("click", function () {
            const itemId = this.dataset.itemid;

            document.querySelectorAll(".item-row").forEach(r => {
                r.classList.remove("selected-row-item");
            });

            this.classList.add("selected-row-item");

            const { projectId } = getCurrentIds();
            history.pushState({}, "", `/home/proj-${projectId}/item-${itemId}`);
        });
    });
}

function updateAddItemUrl(projId, itemId) {
    const btn = document.getElementById("itemAddIcon");
    if (!btn) return;
    btn.href = `/add-item/proj-${projId}/item-${itemId}`;
}


/* =================== EXPORT / COPY =================== */

function exportProj() {
    $('.export_rev_proj').val($('.projrev:checked').data('id'));
}

function copyItem() {
    const selectedRadio = $('.copyrev:checked');
    if (selectedRadio.length) {
        $('.copy_rev_item').val(selectedRadio.data('id'));
    }
}


/* =================== PROJECT ACTIONS =================== */

function submitProject(event, _project) {
    event.preventDefault();
    const { projectId, itemId } = getCurrentIds();

    if (!projectId) return;

    Swal.fire({
        title: "Do you want to submit the project?",
        showDenyButton: true,
        confirmButtonText: "Save",
        denyButtonText: "Cancel",
        customClass: { container: 'swal-custom' }
    }).then(result => {
        if (!result.isConfirmed) return;

        $.ajax({
            type: 'POST',
            url: '/check-project-draftst',
            data: { projectId },
            success: function (response) {
                const first_itemID = response.item_ids ? response.item_ids[0] : itemId;
                const redirectUrl  = `/home/proj-${projectId}/item-${first_itemID}`;

                const doSubmit = () => $.ajax({
                    type: 'POST',
                    url: '/project-submit',
                    data: { projectId },
                    success: function (resp) {
                        if (resp === "success") {
                            Swal.fire({
                                title: 'Project saved successfully',
                                confirmButtonText: 'Ok',
                                icon: 'success',
                                customClass: { container: 'swal-custom' }
                            }).then(r => { if (r.isConfirmed) location.reload(); });
                        } else if (resp === "all completed") {
                            Swal.fire({
                                title: 'No draft available to submit project',
                                confirmButtonText: 'Ok',
                                customClass: { container: 'swal-custom' }
                            });
                        } else {
                            Swal.fire({
                                title: 'Error proceeding further',
                                confirmButtonText: 'Ok',
                                icon: 'error',
                                customClass: { container: 'swal-custom' }
                            });
                        }
                        window.location.href = redirectUrl;
                    }
                });

                if (response.success === 'no') {
                    const error_msg_1 = `Items such as ${response.item_ids} were not saved as draft`;
                    const error_msg_2 = 'Items saved as draft will be submitted';
                    Swal.fire({
                        title: error_msg_2,
                        text: error_msg_1,
                        showDenyButton: true,
                        confirmButtonText: "Ok",
                        denyButtonText: "Cancel",
                        customClass: { container: 'swal-custom' }
                    }).then(r => {
                        if (r.isConfirmed) doSubmit();
                        else window.location.href = redirectUrl;
                    });
                } else {
                    doSubmit();
                }
            },
            error: function () {
                Swal.fire({
                    title: 'An error while saving',
                    confirmButtonText: 'Ok',
                    icon: 'error',
                    customClass: { container: 'swal-custom' }
                });
            }
        });
    });
}

function itemDelete(_itemid) {
    const { projectId, itemId } = getCurrentIds();

    if (!itemId) {
        Swal.fire({ title: "Select an item to delete", confirmButtonText: "Ok" });
        return;
    }

    Swal.fire({
        title: "Do you want to delete the item?",
        showDenyButton: true,
        confirmButtonText: "Delete",
        denyButtonText: "Cancel"
    }).then(result => {
        if (!result.isConfirmed) return;

        Swal.fire({
            title: 'Reason for deleting the item',
            input: 'text',
            inputLabel: 'Enter valid reason',
            showCancelButton: true,
            inputValidator: value => { if (!value) return 'You need to write something!'; }
        }).then(result => {
            if (!result.isConfirmed) return;

            $.ajax({
                type: 'POST',
                url: '/item-delete',
                data: { item_id: itemId, reasonfordelete: result.value },
                success: function (response) {
                    Swal.fire('Deleted!', response.message, 'success');
                    window.location.href = `/home/proj-${projectId}/item-${itemId}`;
                },
                error: function () {
                    Swal.fire('Error!', 'An error occurred while deleting the item', 'error');
                }
            });
        });
    });
}

function projectDelete(_proj) {
    const { projectId } = getCurrentIds();

    Swal.fire({
        title: "Do you want to delete the project?",
        showDenyButton: true,
        confirmButtonText: "Delete",
        denyButtonText: "Cancel"
    }).then(result => {
        if (!result.isConfirmed) return;

        $.ajax({
            type: 'POST',
            url: '/project-delete',
            data: { projectId },
            success: function (response) {
                if ('error-message' in response) {
                    Swal.fire({ icon: 'error', title: 'Permission Denied', text: response['error-message'] });
                } else {
                    window.location.href = `/home/proj-${response.proj}/item-${response.item}`;
                }
            },
            error: function () {
                Swal.fire('Error!', 'An error occurred while deleting the project', 'error');
            }
        });
    });
}


/* =================== REVISION MODAL =================== */

function deleteDraft(itemNo, selectedRev, selectedRevType, _draft_status) {
    if (selectedRevType === 'Completed') {
        alert('Completed Revision cannot be removed');
        return;
    }

    $.ajax({
        type: 'POST',
        url: '/delete-draft',
        data: { itemId: itemNo, itemRevNo: selectedRev, selectedRevType },
        success: function (response) {
            location.reload();
            if (response === 'success') alert("Draft removed successfully");
        },
        error: function () {
            Swal.fire({
                title: 'An error while deleting the draft',
                confirmButtonText: 'Ok',
                icon: 'error',
                customClass: { container: 'swal-custom' }
            });
        }
    });
}

function passRevision(revno, item, draft_status) {
    const { itemId } = getCurrentIds();

    if (item != itemId) {
        const body = $('.rev-body');
        body.empty().append('--- Choose correct item ---');
        $('.modal-footer').empty();
        return;
    }

    revno = parseInt(revno);
    const body = $('.rev-body').empty();

    const table = $('<table>').addClass('tablepopup');
    const thead = $('<thead>');
    const tbody = $('<tbody>');

    const headerRow = $('<tr>');
    headerRow.append($('<th>').text('Select').css({ width: '60px' }));
    headerRow.append($('<th>').text('Revision').css({ width: '70px' }));
    headerRow.append($('<th>').text('Status').css({ width: '140px' }));
    headerRow.append($('<th>').text('Prepared By').css({ width: '80px' }));
    headerRow.append($('<th>').text('Date').css({ width: '120px' }));
    headerRow.append($('<th>').text('Remarks'));
    thead.append(headerRow);
    table.append(thead).append(tbody);

    $.ajax({
        type: 'POST',
        url: '/get-item-revision',
        data: { itemNumber: item },
        success: function (revisions) {
            revisions.forEach(function (revision) {
                const row = $('<tr>');

                const revisionRadio = $('<input>', {
                    type: 'radio',
                    name: 'revision_number',
                    class: 'form-check-input revision_number',
                    'data-id': revision.itemRevisionNo,
                    'data-type': revision.status,
                    'data-user': revision.prepared_by
                }).css('margin-left', '15px');

                row.append($('<td>').append(revisionRadio));
                row.append($('<td>').text(revision.itemRevisionNo));
                row.append($('<td>').text(revision.status));
                row.append($('<td>').text(revision.prepared_by));
                row.append($('<td>').text(formatDateTime(revision.time)));
                row.append($('<td>').text(revision.remarks));
                tbody.append(row);
            });

            $(document).on('change', 'input[type=radio][name=revision_number]', function () {
                if (!this.checked) return;

                const type = $(this).data('type');
                if (type === 'Completed') {
                    $('.goDraftBtn').hide();
                    $('.remDraftBtn').hide();
                    $('.addDraftBtn').show();
                    $('.changeComplRev').show();
                } else {
                    const itemPreparedUsercode = $(this).data('user');
                    if (itemPreparedUsercode === current_user_code && revisions.length > 1) {
                        $('.remDraftBtn').show();
                    } else {
                        $('.remDraftBtn').hide();
                    }
                    $('.changeComplRev').hide();
                    $('.addDraftBtn').hide();
                    $('.goDraftBtn').show();
                }
            });
        },
        error: function () {
            Swal.fire('Error!', 'An error in item revision table', 'error');
        }
    });

    body.append(table);

    const footer = $('.rev-footer').empty();

    const goToDraftBtn = $('<button>', {
        type: 'button',
        class: 'btn btn-outline-success itemrev-btn goDraftBtn',
        'data-dismiss': 'modal',
        click: function () {
            const selectedRevision     = $('input[name="revision_number"]:checked').data('id');
            const selectedRevisionType = $('input[name="revision_number"]:checked').data('type');
            const selectedRevisionUser = $('input[name="revision_number"]:checked').data('user');
            getRevision('existingdraft', item, selectedRevision, selectedRevisionType, draft_status, selectedRevisionUser);
        },
        text: 'Go to draft'
    });

    const addDraftBtn = $('<button>', {
        type: 'button',
        class: 'btn btn-outline-success itemrev-btn addDraftBtn',
        'data-dismiss': 'modal',
        click: function () {
            const selectedRevision     = $('input[name="revision_number"]:checked').data('id');
            const selectedRevisionType = $('input[name="revision_number"]:checked').data('type');
            const selectedRevisionUser = $('input[name="revision_number"]:checked').data('user');
            getRevision('draft', item, selectedRevision, selectedRevisionType, draft_status, selectedRevisionUser);
        },
        text: 'Add a draft'
    });

    const changeCompRev = $('<button>', {
        type: 'button',
        class: 'btn btn-outline-danger itemrev-btn changeComplRev',
        'data-dismiss': 'modal',
        click: function () {
            const selectedRevision     = $('input[name="revision_number"]:checked').data('id');
            const selectedRevisionType = $('input[name="revision_number"]:checked').data('type');
            const selectedRevisionUser = $('input[name="revision_number"]:checked').data('user');
            getRevision('changeCompRev', item, selectedRevision, selectedRevisionType, draft_status, selectedRevisionUser);
        },
        text: 'Edit'
    });

    const previewBtn = $('<button>', {
        type: 'button',
        class: 'btn btn-outline-success itemrev-btn viewBtn',
        'data-dismiss': 'modal',
        click: function () {
            const selectedRevision     = $('input[name="revision_number"]:checked').data('id');
            const selectedRevisionType = $('input[name="revision_number"]:checked').data('type');
            const selectedRevisionUser = $('input[name="revision_number"]:checked').data('user');
            getRevision('view', item, selectedRevision, selectedRevisionType, draft_status, selectedRevisionUser);
        },
        text: 'Preview'
    });

    const removeBtn = $('<button>', {
        type: 'button',
        class: 'btn btn-outline-success itemrev-btn remDraftBtn',
        'data-dismiss': 'modal',
        click: function () {
            const selectedRevision     = $('input[name="revision_number"]:checked').data('id');
            const selectedRevisionType = $('input[name="revision_number"]:checked').data('type');
            deleteDraft(item, selectedRevision, selectedRevisionType, draft_status);
        },
        text: 'Remove Draft'
    });

    footer.append(addDraftBtn).append(previewBtn).append(goToDraftBtn).append(removeBtn).append(changeCompRev);
}

function getRevision(revType, item, selectedRevision, selectedRevisionType, draft_status, selectedRevisionUser) {
    let revisionNumber = selectedRevision;
    let cnt = 0;

    if (draft_status === -1 && revType === 'draft') {
        cnt = 1;
        Swal.fire({
            title: 'Draft is already available for this item. You cannot add another draft',
            confirmButtonText: 'Ok',
            customClass: { container: 'swal-custom' }
        });
    }

    if (selectedRevisionUser !== current_user_code && revType === 'existingdraft' && selectedRevisionType === 'In progress') {
        Swal.fire({
            title: `${selectedRevisionUser} is currently accessing this revision item. Editing is not allowed while another user is accessing it.`,
            confirmButtonText: "Ok",
            customClass: { container: 'swal-custom' }
        });
        cnt = 1;
    }

    if (cnt === 0) {
        $.ajax({
            type: 'POST',
            url: '/change-revision-status',
            data: { revisionType: revType, revisionNumber, itemNumber: item, selectedRevisionType },
            success: function (response) {
                allowNavigation = true;
                if (response[0].itemId && response[1].projId) {
                    window.location.href = `/valve-data/proj-${response[1].projId}/item-${response[0].itemId}`;
                }
            },
            error: function () {
                Swal.fire({
                    title: 'An error while changing the revision status',
                    confirmButtonText: 'Ok',
                    icon: 'error',
                    customClass: { container: 'swal-custom' }
                });
            }
        });
    } else {
        if (selectedRevisionType === 'In progress') {
            revisionNumber = -1;
        } else if (selectedRevisionType === 'Draft Completed') {
            revisionNumber = 0;
        }

        if (selectedRevisionType === 'Completed' && revType === 'existingdraft') {
            alert('No draft available for completed revision');
            return;
        }

        $.ajax({
            type: 'POST',
            url: '/change-revision-status',
            data: { revisionType: revType, revisionNumber, itemNumber: item, selectedRevisionType },
            success: function (response) {
                if (response[0].itemId && response[1].projId) {
                    window.location.href = `/valve-data/proj-${response[1].projId}/item-${response[0].itemId}`;
                }
            },
            error: function () {
                Swal.fire({
                    title: 'An error while changing the revision status',
                    confirmButtonText: 'Ok',
                    icon: 'error',
                    customClass: { container: 'swal-custom' }
                });
            }
        });
    }
}


/* =================== EVENT LISTENERS =================== */

/* copyrev radio change — update copy form action */
document.addEventListener("change", function (e) {
    if (!e.target.classList.contains("copyrev")) return;

    const selectedRev = e.target.value;
    document.querySelector(".copy_rev_item").value = selectedRev;

    const match = window.location.pathname.match(/proj-(\d+)\/item-(\d+)/);
    if (!match) { console.error("Project or Item ID not found in URL"); return; }

    document.getElementById("copyItemForm").action = `/copyItem/proj-${match[1]}/item-${match[2]}`;
});

/* projrev radio change — update export form action */
document.addEventListener("change", function (e) {
    if (!e.target.classList.contains("projrev")) return;

    const selectedRev = e.target.value;
    document.querySelector(".export_rev_proj").value = selectedRev;

    const { projectId, itemId } = getCurrentIds();
    document.getElementById("exportProjForm").action = `/export-project/proj-${projectId}/item-${itemId}`;
});

/* nav-dynamic click — handles data-action links (page-specific actions).
   data-page links are handled by common/header.js. */
document.addEventListener("click", function (e) {
    const link = e.target.closest(".nav-dynamic");
    if (!link) return;

    const action = link.dataset.action;
    if (!action) return;    // data-page links — let header.js handle them

    e.preventDefault();

    const { projectId, itemId } = getCurrentIds();
    if (!projectId) { alert("Please select a project first"); return; }
    switch (action) {
        case "item-revision":
            window.location.href = `/projectRevisionView/proj-${projectId}/item-${itemId}`;
            break;
        case "project-print":
            window.location.href = (window.PROJ_REF === "TESTCASES")
                ? `/generate_csv_testcases/proj-${projectId}/quote-${window.CURRENT_QUOTE}`
                : `/generate_csv_project/proj-${projectId}/item-${itemId}`;
            break;
        case "valvesizingallitems":
            window.location.href = `/valve_sizing_all_items/proj-${projectId}`;
            break;
    }
});

/* Item Add icon click — set href before navigation */
$('#itemAddIcon').on('click', function () {
    const { projectId, itemId } = getCurrentIds();
    updateAddItemUrl(projectId, itemId);
});

/* Project row click — load items for selected project */
document.getElementById("projectlist").addEventListener("click", function (e) {
    const row = e.target.closest(".project-row");
    if (!row) return;

    const projectId = row.getAttribute("data-projid");
    if (!projectId) return;

    /* Deselect all project rows */
    document.getElementsByClassName("project-row").forEach
        ? Array.from(document.getElementsByClassName("project-row")).forEach(r => {
            r.classList.remove("selected-row-project");
            const radio = r.getElementsByTagName("input")[0];
            if (radio) radio.checked = false;
        })
        : (() => {
            const rows = document.getElementsByClassName("project-row");
            for (let i = 0; i < rows.length; i++) {
                rows[i].classList.remove("selected-row-project");
                const radio = rows[i].getElementsByTagName("input")[0];
                if (radio) radio.checked = false;
            }
        })();

    /* Select current row */
    row.classList.add("selected-row-project");
    const radio = row.getElementsByTagName("input")[0];
    if (radio) radio.checked = true;

    document.getElementById("itemsLoader").style.display = "block";

    fetch(`/get_items_only/proj-${projectId}`)
        .then(res => res.json())
        .then(data => {
            updateItemsList(data.items);
            if (data.items && data.items.length > 0) {
                history.pushState(
                    { projId: projectId, itemId: data.items[0].itemId },
                    "",
                    `/home/proj-${projectId}/item-${data.items[0].itemId}`
                );
            }
        })
        .catch(err => console.error("Item load error:", err))
        .finally(() => { document.getElementById("itemsLoader").style.display = "none"; });
});

/* Initial page load — populate item table from URL */
document.addEventListener("DOMContentLoaded", function () {
    const { projectId, itemId } = getCurrentIds();
    const isRandom = document.getElementById('randomData').value;

    if (isRandom === 'yes') {
        const tbody = document.getElementById("itemsTableBody");
        $(".project-row").removeClass("active selected-row-project");
        $(".project-radio").prop('checked', false);
        tbody.innerHTML = `
            <tr>
                <td colspan="100%" style="text-align:center; padding:12px; color:#666;">
                    Select Project to display items
                </td>
            </tr>`;
        return;
    }

    fetch(`/get_items_only/proj-${projectId}`)
        .then(res => res.json())
        .then(data => {
            updateItemsList(data.items);
            if (itemId) selectItemRow(itemId);
        })
        .catch(err => console.error("Initial item load failed:", err));
});

/* Browser back/forward — restore item list for navigated state */
window.addEventListener("popstate", function (event) {
    if (!event.state) return;

    const { projId, itemId } = event.state;
    fetch(`/get_items_only/proj-${projId}`)
        .then(res => res.json())
        .then(data => {
            updateItemsList(data.items);
            setTimeout(() => {
                const row = document.querySelector(`.item-row[data-itemid="${itemId}"]`);
                if (row) row.click();
            }, 50);
        });
});

/* jQuery ready — scroll selected item into view, sync proj-type */
$(document).ready(function () {
    const selectedItemRow = $(".selected-row-item");
    if (selectedItemRow.length) {
        tablecontainer2.scrollTo({
            top: selectedItemRow.offset().top - 470,
            behavior: "smooth"
        });
    }
// on change PROJECT TYPE reload   test case / live projects
    $('.project-type').on('change', function(){
        const proj_type = $('.project-type').val();
        $.ajax({
            type: 'GET',
            url: '/submit-project-type',
            data: { proj_type },
            success: function(){
                location.reload();
            }
        });
    });

    /* Export project modal — load revisions dynamically */
    $(document).on('show.bs.modal', '#exportProjModal', function () {
        const fccUser   = document.getElementById('isFccProject').value === 'true';
        const { projectId } = getCurrentIds();
        const modalBody = document.getElementById("exportProjModalBody");

        modalBody.innerHTML = '<p class="text-center">Loading revisions...</p>';

        fetch(`/get_project_revisions/${projectId}`)
            .then(res => res.json())
            .then(data => {
                let html = '';
                data.forEach(rev => {
                    const revVal   = fccUser ? rev.projectRevision : 0;
                    const revLabel = fccUser ? `Revision ${rev.projectRevision}` : `Revision 0`;
                    html += `
                        <div class="row ml-4">
                            <div class="form-check">
                                <input class="form-check-input projrev" type="radio"
                                    name="proj_rev" data-id="${revVal}" value="${revVal}">
                                <label class="form-check-label project_lable">${revLabel}</label>
                            </div>
                        </div>`;
                });
                modalBody.innerHTML = html;
            })
            .catch(() => {
                modalBody.innerHTML = '<p class="text-danger text-center">Failed to load revisions</p>';
            });
    });

    /* Copy item modal — load item revisions dynamically */
    $(document).on('show.bs.modal', '#copyItemModal', function () {
        const fccUser = document.getElementById('isFccProject').value === 'true';
        const match   = window.location.pathname.match(/item-(\d+)/);
        if (!match) { console.warn("No item selected"); return; }

        const itemId    = match[1];
        const modalBody = document.getElementById("copyItemModalBody");
        modalBody.innerHTML = '<p class="text-center">Loading revisions...</p>';

        fetch(`/get_item_revisions/item-${itemId}`)
            .then(res => res.json())
            .then(data => {
                let html = '';
                data.forEach(rev => {
                    if (!fccUser) {
                        html += `
                            <div class="row ml-4"><div class="form-check">
                                <input class="form-check-input copyrev" type="radio" name="copy_rev" data-id="0" value="0">
                                <label class="form-check-label project_lable">${rev.itemRevisionNo ?? rev.status}</label>
                            </div></div>`;
                        return;
                    }
                    if (rev.status === 'Completed') {
                        html += `
                            <div class="row ml-4"><div class="form-check">
                                <input class="form-check-input copyrev" type="radio" name="copy_rev"
                                    data-id="${rev.itemRevisionNo}" value="${rev.itemRevisionNo}">
                                <label class="form-check-label project_lable">Revision ${rev.itemRevisionNo}</label>
                            </div></div>`;
                    } else if (rev.status === 'In progress') {
                        html += `
                            <div class="row ml-4"><div class="form-check">
                                <input class="form-check-input copyrev" type="radio" name="copy_rev" data-id="-1" value="-1">
                                <label class="form-check-label project_lable">${rev.status}</label>
                            </div></div>`;
                    } else if (rev.status === 'Draft Completed') {
                        html += `
                            <div class="row ml-4"><div class="form-check">
                                <input class="form-check-input copyrev" type="radio" name="copy_rev" data-id="0" value="0">
                                <label class="form-check-label project_lable">${rev.status}</label>
                            </div></div>`;
                    }
                });
                modalBody.innerHTML = html;
            })
            .catch(() => {
                modalBody.innerHTML = '<p class="text-danger text-center">Failed to load revisions</p>';
            });
    });
});


/* =================== INTRO.JS TOUR =================== */

document.addEventListener('DOMContentLoaded', () => {
    const username = document.getElementById('username').value;

    const STEPS = [
        { intro: `Welcome ${username}! Here's a quick tour to get you started.` },
        { element: "#projectAddBtn",  intro: "Click here to create a new project." },
        { element: "#exportProjIcon", intro: "Export the selected project." },
        { element: "#importProjIcon", intro: "Import an exported project." },
        { element: "#projectinput",   intro: "Search for projects by quote, customer, or enquiry reference.", position: "bottom" },
        { element: "#itemAddIcon",    intro: "Click here to create a new item." },
        { element: "#copyItemIcon",   intro: "Click here to duplicate the selected item." },
        { element: "#iteminput",      intro: "Search for items within the selected project.", position: "bottom" },
        { element: "#projectDetails", intro: "Enter the project & customer details in this section.", position: "right" },
        { element: "#valveData",      intro: "Enter the valve specification in this section.", position: "right" },
        { element: "#valveSizing",    intro: "Perform valve sizing and select the appropriate valve here.", position: "right" },
        { element: "#actSizing",      intro: "Size the actuator in this section.", position: "right" },
        { element: "#accessories",    intro: "Specify the required accessories here.", position: "right" },
        { element: "#itemNotes",      intro: "Add notes for the selected item here.", position: "right" },
        { element: "#projectPrint",   intro: "Download the project specification sheet, which includes all items." },
        { element: "#itemPrint",      intro: "Download the specification sheet for the selected item." },
        { intro: "That's it! You're now ready to get started." }
    ];

    const NAME    = "dashboard";
    const AUTORUN = true;
    const opts    = {
        tooltipClass:       'tour-theme',
        showProgress:       false,
        showBullets:        false,
        scrollToElement:    true,
        exitOnOverlayClick: true,
        nextLabel:  'Next',
        prevLabel:  'Back',
        skipLabel:  'Skip',
        doneLabel:  'Finish'
    };

    if (AUTORUN && !Tour.isDone(NAME)) {
        Tour.start(NAME, STEPS, opts);
    }

    document.getElementById('dashboardTourBtn')?.addEventListener('click', () => {
        Tour.reset(NAME);
        Tour.start(NAME, STEPS, opts);
    });
});

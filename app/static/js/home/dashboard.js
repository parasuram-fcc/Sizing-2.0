/* =============================================
   dashboard.js — Home / Dashboard page logic

   Jinja2 values are passed via hidden <input> elements
   in the template (ids: adminUser, currentUserCode,
   isFccProject, projRef, currentQuote, username, randomData).
   ============================================= */


/* =================== GLOBAL STATE & INIT =================== */

let adminUser = '';
let current_user_code = '';
let isFccUser = false;

let projectsearchType = 'customer';
let itemsearchType = 'tagNo';
let debounceTimer;
let currentRequestId = 0;
let projectLoadRequestId = 0;

document.addEventListener('DOMContentLoaded', function () {
    adminUser         = document.getElementById('adminUser').value;
    current_user_code = document.getElementById('currentUserCode').value;
    isFccUser         = document.getElementById('isFccProject').value === 'true';
    window.PROJ_REF       = document.getElementById('projRef').value;
    window.CURRENT_QUOTE  = document.getElementById('currentQuote').value;
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


/* =================== TOPBAR =================== */

// --- Search ---

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
        if (row_type === 'project') {
            const projType = parseInt(document.getElementById('projectType').value || '1', 10);
            if (projType === 2) {
                loadTestcaseProjects();
            } else {
                loadProjects();
            }
        } else if (row_type === 'item') {
            const requestId = ++currentRequestId;
            let url = window.location.pathname;
            url += `?type=item&search_type=${searchType}&search_value=${value}`;
            fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } })
                .then(res => res.json())
                .then(data => {
                    if (requestId !== currentRequestId) return;
                    updateItemsList(data.items);
                });
        }
    }, 300);
}

// --- Quote range switch ---

$("#bucketSelect").on('change', function () {
    loadProjects(this.value);
});

// --- Project type switch ---

$(document).ready(function () {
    const selectedItemRow = $(".selected-row-item");
    if (selectedItemRow.length) {
        tablecontainer2.scrollTo({
            top: selectedItemRow.offset().top - 470,
            behavior: "smooth"
        });
    }

    // on change PROJECT TYPE — save to DB, then dynamically refresh project & item tables
    $('.project-type').on('change', function () {
        const proj_type = $('.project-type').val();

        $.ajax({
            type: 'GET',
            url: '/project/submit-project-type',
            data: { proj_type },
            success: function () {
                const bucketSelect = document.getElementById('bucketSelect');
                if (proj_type === '2') {
                    if (bucketSelect) bucketSelect.style.display = 'none';
                    loadTestcaseProjects();
                } else {
                    if (bucketSelect) bucketSelect.style.display = '';
                    resetItemTable();
                    loadProjects();
                }
            },
            error: function () {
                console.error('Failed to update project type');
            }
        });
    });
});


/* =================== PROJECT =================== */

const table_loader = `
        <tr><td colspan="100%" style="text-align:center;padding:14px;">
            <div class="spinner" style="width:20px;height:20px;border-width:3px;margin:0 auto;"></div>
        </td></tr>`;

/**
 * Fetch live projects from /load_projects and render them.
 * quoteRange — bucket string; if omitted, server uses the session value.
 * Called when projType == 1.
 */
function loadProjects(quoteRange) {
    const tbody = document.getElementById("projectTableBody");
    const requestId = ++projectLoadRequestId;

    // Reset item table when switching buckets or on initial no-selection load
    if (quoteRange) resetItemTable();

    // Show spinner while loading // add loader
    tbody.innerHTML = table_loader;

    const params = new URLSearchParams();
    if (quoteRange) params.append('quote_range', quoteRange);

    const searchValue = document.getElementById("search_input").value.trim();
    if (searchValue) {
        params.append('search_type',  projectsearchType);
        params.append('search_value', searchValue);
    }

    const qs  = params.toString();
    const url = '/load_projects' + (qs ? '?' + qs : '');

    fetch(url)
        .then(res => res.json())
        .then(data => {
            if (requestId !== projectLoadRequestId) return;   // stale response
            const { projectId } = getCurrentIds();
            updateProjectsList(data.projects, projectId);
            resetItemTable();
        })
        .catch(err => {
            console.error("Project load error:", err);
            tbody.innerHTML = `<tr><td colspan="100%" style="text-align:center;padding:12px;color:#c00;">Error loading projects</td></tr>`;
        });
}

/**
 * Fetch testcase projects from /load_testcase_projects and render them.
 * Called when projType == 2 (FCC users only).
 */
function loadTestcaseProjects() {
    const tbody     = document.getElementById("projectTableBody");
    const requestId = ++projectLoadRequestId;

    resetItemTable();

    tbody.innerHTML = table_loader;

    const params = new URLSearchParams();
    const searchValue = document.getElementById("search_input").value.trim();
    if (searchValue) {
        params.append('search_type',  projectsearchType);
        params.append('search_value', searchValue);
    }

    const qs  = params.toString();
    const url = '/load_testcase_projects' + (qs ? '?' + qs : '');

    fetch(url)
        .then(res => res.json())
        .then(data => {
            if (requestId !== projectLoadRequestId) return;
            const { projectId } = getCurrentIds();
            updateProjectsList(data.projects, projectId);
        })
        .catch(err => {
            console.error("Testcase project load error:", err);
            tbody.innerHTML = `<tr><td colspan="100%" style="text-align:center;padding:12px;color:#c00;">Error loading projects</td></tr>`;
        });
}

/**
 * Render project rows into #projectTableBody.
 * selectedProjId — highlight the matching row (from URL or first-load).
 */
function updateProjectsList(projects, selectedProjId) {
    const tbody = document.getElementById("projectTableBody");
    tbody.innerHTML = "";

    if (!projects || projects.length === 0) {
        tbody.innerHTML = `<tr><td colspan="100%" style="text-align:center;padding:12px;color:#666;">No projects to display</td></tr>`;
        return;
    }

    projects.forEach(proj => {
        const isSelected  = selectedProjId && String(proj.id) === String(selectedProjId);
        const printPage   = proj.projectRef === 'TESTCASES' ? 'valve_sizing_all_items' : 'generate_csv_project';

    // hiding status, work order number from dashboard
    // <td class="table1_status pdl-4">${proj.status}</td>
    // <td class="table1_work pdl-4">${proj.workOrderNo}</td>
        const row = `
        <tr class="project-row${isSelected ? ' selected-row-project' : ''}"
            data-projid="${proj.id}" style="cursor:pointer">
            <td class="table1_quote">${proj.quoteNo}</td>
            <td class="table1_customer pdl-4">${proj.customerName}</td>
            <td class="table1_enquiry pdl-4">${proj.enquiryRef}</td>
            <td class="table1_receipt pdl-4">${proj.receiptDate}</td>
            <td class="table1_due pdl-4">${proj.dueDate}</td>
            <td class="table1_region pdl-4">${proj.region}</td>
            <td class="table1_industry pdl-4">${proj.industry}</td>
            <td class="table1_engineer pdl-4">${proj.engineerName}</td>

            <td class="table1_work">
                <a class="nav-dynamic" data-page="projectRevisionView" href="#">
                    <i class="fa-solid fa-eye"></i>
                </a>
            </td>
            <td class="table1_print">
                <a class="nav-dynamic" data-page="${printPage}" href="#">
                    <i class="fa-solid fa-print"></i>
                </a>
            </td>
        </tr>`;
        tbody.insertAdjacentHTML("beforeend", row);
    });
}

function selectProjectRow(projectId) {
    document.querySelectorAll(".project-row").forEach(row => {
        row.classList.remove("selected-row-project");
        if (row.dataset.projid == projectId) {
            row.classList.add("selected-row-project");
            sessionStorage.setItem('proj_id', projectId);
        }
    });
}

function projectDelete(_proj) {
    const projectId = String(_proj);

    Swal.fire({
        title: "Do you want to delete the project?",
        showDenyButton: true,
        confirmButtonText: "Delete",
        denyButtonText: "Cancel"
    }).then(result => {
        if (!result.isConfirmed) return;
        $.ajax({
            type: 'POST',
            url: '/project/project-delete',
            contentType: 'application/json',
            data: JSON.stringify({ projectId }),
            success: function (response) {

                // Silently remove the deleted project row
                const deletedRow = document.querySelector(`tr[data-projid="${projectId}"]`);
                if (deletedRow) deletedRow.remove();

                sessionStorage.removeItem('proj_id');
                sessionStorage.removeItem('item_id');
                resetItemTable();

                showFlash(response.message, 'success');
            },
            error: function (xhr) {
                var resp = JSON.parse(xhr.responseText);
                showFlash(resp.message, resp.status)  ;
            }
        });
    });
}

function submitProject() {
    const { projectId, itemId } = getCurrentIds();

    if (!projectId) return;

    Swal.fire({
        title: "Do you want to submit the project?",
        showDenyButton: true,
        confirmButtonText: "Yes",
        denyButtonText: "Cancel",
        customClass: { container: 'swal-custom' }
    }).then(result => {
        if (!result.isConfirmed) return;

        $.ajax({
            type: 'POST',
            url: '/project/check-project-draftst',
            data: { projectId },
            success: function (response) {
                const first_itemID = response.item_ids ? response.item_ids[0] : itemId;
                sessionStorage.setItem('proj_id', projectId);
                sessionStorage.setItem('item_id', first_itemID);
                // const redirectUrl = '/home';

                const doSubmit = () => $.ajax({
                    type: 'POST',
                    url: '/project/project-submit',
                    data: { projectId },
                    success: function (resp) {
                        if (resp.status === "success") {
                            Swal.fire({
                                title: 'Project saved successfully',
                                confirmButtonText: 'Ok',
                                icon: 'success',
                                customClass: { container: 'swal-custom' }
                            }).then(r => { if (r.isConfirmed)
                                getItemsByProject(projectId, items => {
                                    updateItemsList(items);
                                    if (itemId) selectItemRow(itemId);
                                });
                                return;});
                        } else {
                            Swal.fire({
                                title: 'Error proceeding further',
                                confirmButtonText: 'Ok',
                                icon: 'error',
                                customClass: { container: 'swal-custom' }
                            });
                        }
                        // window.location.href = redirectUrl;
                    },
                    error: function(xhr){
                        const resp = JSON.parse(xhr.responseText);
                        showFlash(resp.message, resp.message);
                    }
                });

                // has_submitable=false cases are handled here — no doSubmit needed
                if (!response.has_submitable) {
                    if (response.reason === 'all_completed') {
                        Swal.fire({
                            title: 'All drafts are already submitted',
                            confirmButtonText: 'Ok',
                            customClass: { container: 'swal-custom' }
                        });
                    } else if (response.reason === 'no_drafts') {
                        Swal.fire({
                            title: 'No drafts available to submit the project',
                            text: 'Submit one draft and Try again !',
                            confirmButtonText: 'Ok',
                            customClass: { container: 'swal-custom' }
                        });
                    }
                    return;
                } else {
                    if (response.item_ids) {
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
                        });
                    } else {
                        doSubmit();
                    }
                }
            },
            error: function (xhr) {
                var resp = JSON.parse(xhr.responseText);
                showFlash("An error while saving", resp.status)
            }
        });
    });
}

/* Project Add button click — navigate to add-project page */
$('#projectAddBtn').on('click', function () {
    allowNavigation = true;
    window.location.href = `/project/add-project/`;
});

$('#projectDeleteBtn').on('click', function(){
    proj_id = sessionStorage.getItem('proj_id');
    projectDelete(proj_id);
})
$('#submitProjectBtn').on('click', function(e){
    e.preventDefault();
    submitProject();
})

/* Initial page load — populate project table, then item table */
document.addEventListener("DOMContentLoaded", function () {
    const { projectId, itemId } = getCurrentIds();
    const isRandom = document.getElementById('randomData').value;

    // Load the correct project list based on projType
    const projType = parseInt(document.getElementById('projectType').value || '1', 10);
    if (projType === 2) {
        loadTestcaseProjects();
    } else {
        loadProjects();
    }

    if (isRandom === 'yes') {
        resetItemTable();
        return;
    }

    getItemsByProject(projectId, items => {
        updateItemsList(items);
        if (itemId) selectItemRow(itemId);
    });
});

/* Project row click — load items for selected project */
$("#projectTableBody").on("click", function (e) {
    const row = e.target.closest(".project-row");
    if (!row) return;

    const projectId = row.getAttribute("data-projid");
    if (!projectId) return;

    selectProjectRow(projectId);

    const tbody = document.getElementById("itemsTableBody");
    tbody.innerHTML = table_loader;

    getItemsByProject(projectId, items => {
        updateItemsList(items);
        if (items && items.length > 0) selectItemRow(items[0].itemId);
    });
});


/* =================== ITEM =================== */

function getItemsByProject(projectId, onSuccess) {
    fetch(`/project/get_items_only/proj-${projectId}`)
        .then(res => res.json())
        .then(data => onSuccess(data.items))
        .catch(() => showFlash("Failed to load items. Please try again.", "error"));
}

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

}

function resetItemTable() {
    document.getElementById("itemsTableBody").innerHTML = `
        <tr>
            <td colspan="100%" style="text-align:center;padding:12px;color:#666;">
                Select Project to display items
            </td>
        </tr>`;
}

function selectItemRow(itemId) {
    document.querySelectorAll(".item-row").forEach(row => {
        row.classList.remove("selected-row-item");
        if (row.dataset.itemid == itemId) {
            row.classList.add("selected-row-item");
            sessionStorage.setItem('item_id', itemId);
        }
    });
}

$('#itemsTableBody').on('click', function(e){
    const row = e.target.closest('.item-row');
    if (!row){
        return;
    }
    const itemId = row.getAttribute('data-itemid');
    if (!itemId){
        return;
    }
    selectItemRow(itemId);
});

/* Item Add icon click — POST to add-item REST API */
$('#itemAddIcon').on('click', function (e) {
    e.preventDefault();
    const { projectId } = getCurrentIds();
    if (!projectId) {
        Swal.fire({ title: "Select a project first", confirmButtonText: "Ok" });
        return;
    }
    $.ajax({
        type: 'POST',
        url: '/project/add-item',
        contentType: 'application/json',
        data: JSON.stringify({ project_id: projectId }),
        success: function (response) {
            showFlash(response.message, 'success');
            document.getElementById("itemsTableBody").innerHTML = table_loader;
            getItemsByProject(projectId, items => {
                updateItemsList(items);
                if (response.item_id) selectItemRow(response.item_id);
            });
        },
        error: function (xhr) {
            const resp = JSON.parse(xhr.responseText);
            showFlash(resp.message, 'error');
        }
    });
});

/* Item Delete icon click — trigger itemDelete */
$('#itemDeleteBtn').on('click', function () {
    itemDelete();
});

// add event listener for delete.
function itemDelete(_itemid) { // check for
    const { itemId } = getCurrentIds();

    if (!itemId) {
        Swal.fire({ title: "Select an item to delete", confirmButtonText: "Ok" });
        return;
    }

    Swal.fire({
        title: "Do you want to delete the item?",
        showDenyButton: true,
        confirmButtonText: "Delete",
        denyButtonText: "Cancel",
        customClass: { container: 'swal-custom' }
    }).then(result => {
        if (!result.isConfirmed) return;

        Swal.fire({
            title: 'Reason for deleting the item',
            input: 'text',
            inputLabel: 'Enter valid reason',
            showCancelButton: true,
            customClass: { container: 'swal-custom' },
            inputValidator: value => { if (!value) return 'You need to write something!'; }
        }).then(result => {
            if (!result.isConfirmed) return;

            $.ajax({
                type: 'POST',
                url: '/project/item-delete',
                contentType: 'application/json',
                data: JSON.stringify({ item_id: itemId, reasonfordelete: result.value }),
                success: function (response) {
                    showFlash(response.message, 'success');
                    sessionStorage.removeItem('item_id');
                    const { projectId } = getCurrentIds();
                    document.getElementById("itemsTableBody").innerHTML = table_loader;
                    getItemsByProject(projectId, items => {
                        updateItemsList(items);
                        if (response.item_id) selectItemRow(response.item_id);
                    });
                },
                error: function (xhr) {
                    const resp = JSON.parse(xhr.responseText);
                    showFlash(resp.message, 'error');
                }
            });
        });
    });
}

/* Browser back/forward — restore item list for navigated state */
window.addEventListener("popstate", function (event) {
    if (!event.state) return;

    const { projId, itemId } = event.state;
    getItemsByProject(projId, items => {
        updateItemsList(items);
    });
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


/* =================== REVISION =================== */

function deleteDraft(itemNo, selectedRev, selectedRevType, _draft_status) {
    if (selectedRevType === 'Completed') {
        alert('Completed Revision cannot be removed');
        return;
    }

    $.ajax({
        type: 'POST',
        url: '/project/delete-draft',
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
        url: '/project/get-item-revision',
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
            url: '/project/change-revision-status',
            data: { revisionType: revType, revisionNumber, itemNumber: item, selectedRevisionType },
            success: function (response) {
                allowNavigation = true;
                if (response[0].itemId && response[1].projId) {
                    sessionStorage.setItem('proj_id', response[1].projId);
                    sessionStorage.setItem('item_id', response[0].itemId);
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
            url: '/project/change-revision-status',
            data: { revisionType: revType, revisionNumber, itemNumber: item, selectedRevisionType },
            success: function (response) {
                if (response[0].itemId && response[1].projId) {
                    sessionStorage.setItem('proj_id', response[1].projId);
                    sessionStorage.setItem('item_id', response[0].itemId);
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

/* Copy item modal — load item revisions dynamically */
$(document).on('show.bs.modal', '#copyItemModal', function () {
    const fccUser = document.getElementById('isFccProject').value === 'true';
    const { itemId } = getCurrentIds();
    if (!itemId) { console.warn("No item selected"); return; }

    const modalBody = document.getElementById("copyItemModalBody");
    modalBody.innerHTML = '<p class="text-center">Loading revisions...</p>';

    fetch(`/project/get_item_revisions/item-${itemId}`)
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


/* =================== IMPORT / EXPORT =================== */

/* ExpotrProjectBtn click — send selected revision as query param to REST export endpoint */
$('#ExpotrProjectBtn').on('click', function () {
    const selectedRev = $('.projrev:checked').val();
    if (selectedRev === undefined) {
        showFlash('Please select a revision to export', 'warning');
        return;
    }

    const { projectId, itemId } = getCurrentIds();
    if (!projectId || !itemId) {
        showFlash('No project selected', 'warning');
        return;
    }

    $.ajax({
        type: 'GET',
        url: `/project/export-project?proj_id=${projectId}&item_id=${itemId}&export_proj=${selectedRev}`,
        xhrFields: { responseType: 'blob' },
        success: function (blob, _status, xhr) {
            const url = window.URL.createObjectURL(blob);
            const a   = document.createElement('a');
            a.href    = url;

            /* Try to get filename from Content-Disposition header */
            const disposition = xhr.getResponseHeader('Content-Disposition');
            let filename = 'export.xlsx';
            if (disposition) {
                const match = disposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
                if (match) filename = match[1].replace(/['"]/g, '');
            }

            a.download = filename;
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(url);
            $('#exportProjModal').modal('hide');
        },
        error: function (xhr) {
            const reader = new FileReader();
            reader.onload = function () {
                try {
                    const resp = JSON.parse(reader.result);
                    showFlash(resp.message || 'Export failed', 'error');
                } catch (_) {
                    showFlash('Export failed', 'error');
                }
            };
            reader.readAsText(xhr.responseText instanceof Blob ? xhr.responseText : new Blob([xhr.responseText]));
        }
    });
});

/* Copy item button click — POST to copy-item REST API */
$('#copyItemBtn').on('click', function () {
    const selectedRadio = $('.copyrev:checked');
    if (!selectedRadio.length) {
        showFlash('Please select a revision to copy', 'warning');
        return;
    }

    const { projectId, itemId } = getCurrentIds();
    if (!projectId || !itemId) {
        showFlash('Select a project and item first', 'warning');
        return;
    }

    $.ajax({
        type: 'POST',
        url: '/project/copy-item',
        contentType: 'application/json',
        data: JSON.stringify({
            project_id: projectId,
            item_id: itemId,
            copy_rev: selectedRadio.data('id')
        }),
        success: function (response) {
            $('#copyItemModal').modal('hide');
            showFlash(response.message, 'success');
            document.getElementById("itemsTableBody").innerHTML = table_loader;
            getItemsByProject(projectId, items => {
                updateItemsList(items);
                if (response.item_id) selectItemRow(response.item_id);
            });
        },
        error: function (xhr) {
            const resp = JSON.parse(xhr.responseText);
            showFlash(resp.message, 'error');
        }
    });
});

/* projrev radio change — update export form action */
document.addEventListener("change", function (e) {
    if (!e.target.classList.contains("projrev")) return;

    const selectedRev = e.target.value;
    document.querySelector(".export_rev_proj").value = selectedRev;
});

/* Export project modal — load revisions dynamically */
$(document).on('show.bs.modal', '#exportProjModal', function () {
    const fccUser   = document.getElementById('isFccProject').value === 'true';
    const { projectId } = getCurrentIds();
    const modalBody = document.getElementById("exportProjModalBody");

    modalBody.innerHTML = '<p class="text-center">Loading revisions...</p>';

    fetch(`/project/get_project_revisions/${projectId}`)
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

/* Import project modal — setup form and quote validation */
$(document).on('show.bs.modal', '#importProjModal', function () {
    const { projectId, itemId } = getCurrentIds();
    const isFcc     = document.getElementById('isFccProject').value === 'true';
    const projType  = parseInt(document.getElementById('projectType').value || '1', 10);
    const quoteField    = document.getElementById('importQuoteField');
    const quoteInput    = document.getElementById('importQuoteNo');
    const quoteFeedback = document.getElementById('importQuoteFeedback');
    const form          = document.getElementById('importProjForm');

    /* Set form action to the current project/item */
    form.action = `/project/import-project/proj-${projectId}/item-${itemId}`;

    /* Show quote field only for FCC live users */
    const needsQuote = isFcc && projType === 1;
    quoteField.style.display = needsQuote ? '' : 'none';
    quoteInput.required      = needsQuote;

    /* Reset state */
    quoteInput.value    = '';
    quoteFeedback.textContent = '';
    quoteFeedback.className   = 'form-text';
    document.getElementById('importProjFile').value = '';

    /* Submit button: disabled until quote is validated (FCC only) */
    $('#importProjSubmitBtn').prop('disabled', needsQuote);
});

/* Quote number live validation — delegate to shared validateAndCheckQuote */
$(document).on('input', '#importQuoteNo', function () {
    validateAndCheckQuote('#importQuoteNo', '#importQuoteFeedback', '#importProjSubmitBtn');
});

/* Import submit handler */
$(document).on('click', '#importProjSubmitBtn', function () {
    const file = document.getElementById('importProjFile').files[0];
    if (!file) {
        document.getElementById('importProjFile').reportValidity();
        return;
    }

    document.getElementById('importProjForm').submit();
});


/* =================== TOUR =================== */

document.addEventListener('DOMContentLoaded', () => {
    const username = document.getElementById('username').value;

    const STEPS = [
        { intro: `Welcome ${username}! Here's a quick tour to get you started.` },
        { element: "#projectAddBtn",  intro: "Click here to create a new project." },
        { element: "#exportProjIcon", intro: "Export the selected project." },
        { element: "#importProjIcon", intro: "Import an exported project." },
        { element: "#search_input",    intro: "Search for projects by quote, customer, or enquiry reference.", position: "bottom" },
        { element: "#itemAddIcon",    intro: "Click here to create a new item." },
        { element: "#copyItemIcon",   intro: "Click here to duplicate the selected item." },
        { element: "#search_input_item", intro: "Search for items within the selected project.", position: "bottom" },
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

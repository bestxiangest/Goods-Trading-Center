// 全局变量
let currentSection = 'dashboard';
let currentPage = 1;
let pageSize = 10;
// 移除token相关变量

// Chart.js 实例管理
let userChart = null;
let categoryChart = null;


// API基础URL
const API_BASE_URL = 'http://localhost:5000/api/v1';

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    // 检查登录状态
    checkAuthStatus();
});

// 检查认证状态
function checkAuthStatus() {
    // 检查是否已登录（简单检查localStorage中的标记）
    const isLoggedIn = localStorage.getItem('admin_logged_in');
    
    if (!isLoggedIn) {
        // 如果没有登录标记，重定向到登录页面
        window.location.href = '/login';
        return;
    }
    
    // 简单验证（不使用token）
    fetch(`${API_BASE_URL}/users/verify`, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('验证失败');
        }
        return response.json();
    })
    .then(data => {
        if (data.data && data.data.is_admin) {
            // 使用保存的用户名
            const savedUsername = localStorage.getItem('admin_username') || 'admin';
            document.getElementById('admin-username').textContent = savedUsername;
            // 只有在认证成功后才初始化页面和加载数据
            initializeAdminPanel();
        } else {
            throw new Error('非管理员');
        }
    })
    .catch(error => {
        console.error('认证检查失败:', error);
        logout();
    });
}

// 初始化管理面板
function initializeAdminPanel() {
    // 初始化仪表盘
    showSection('dashboard');
    
    // 加载初始数据
    loadDashboardData();
}

// 退出登录
function logout() {
    localStorage.removeItem('admin_logged_in');
    localStorage.removeItem('admin_username');
    localStorage.removeItem('remember_admin');
    window.location.href = '/login';
}

// 显示指定的内容区域
function showSection(sectionName) {
    // 隐藏所有内容区域
    const sections = document.querySelectorAll('.content-section');
    sections.forEach(section => {
        section.style.display = 'none';
    });
    
    // 显示指定区域
    const targetSection = document.getElementById(`${sectionName}-section`);
    if (targetSection) {
        targetSection.style.display = 'block';
    }
    
    // 更新导航状态
    const navLinks = document.querySelectorAll('.sidebar .nav-link');
    navLinks.forEach(link => {
        link.classList.remove('active');
    });
    
    const activeLink = document.querySelector(`[onclick="showSection('${sectionName}')"]`);
    if (activeLink) {
        activeLink.classList.add('active');
    }
    
    currentSection = sectionName;
    
    // 根据不同区域加载相应数据
    switch(sectionName) {
        case 'dashboard':
            loadDashboardData();
            break;
        case 'users':
            currentPage = 1; // 重置页码
            loadUsers();
            break;
        case 'items':
            currentPage = 1; // 重置页码
            loadItems();
            loadCategories(); // 为筛选器加载分类
            break;
        case 'categories':
            currentPage = 1; // 重置页码
            loadCategories();
            break;
        case 'requests':
            currentPage = 1; // 重置页码
            loadRequests();
            break;
        case 'reviews':
            currentPage = 1; // 重置页码
            loadReviews();
            break;
        case 'messages':
            currentPage = 1; // 重置页码
            loadMessages();
            break;

    }
}

// 通用API请求函数
function apiRequest(url, options = {}) {
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json'
        }
    };
    
    const mergedOptions = {
        ...defaultOptions,
        ...options,
        headers: {
            ...defaultOptions.headers,
            ...options.headers
        }
    };
    
    return fetch(`${API_BASE_URL}${url}`, mergedOptions)
        .then(response => {
            if (!response.ok) {
                return response.json().then(errorData => {
                    throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
                }).catch(() => {
                    throw new Error(`HTTP error! status: ${response.status}`);
                });
            }
            // 处理204 No Content响应
            if (response.status === 204) {
                return { success: true, message: '操作成功' };
            }
            return response.json();
        })
        .catch(error => {
            console.error('API request failed:', error);
            throw error;
        });
}

// 显示提示信息
function showAlert(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    // 插入到主要内容区域的顶部
    const main = document.querySelector('main');
    main.insertBefore(alertDiv, main.firstChild);
    
    // 3秒后自动消失
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.remove();
        }
    }, 3000);
}

// 加载仪表盘数据
function loadDashboardData() {
    // 加载统计数据
    Promise.all([
        apiRequest('/users/count'),
        apiRequest('/items/count'),
        apiRequest('/requests/count?status=pending'),
        apiRequest('/today')
    ])
    .then(([usersCount, itemsCount, pendingRequests, todayStats]) => {
        document.getElementById('total-users').textContent = usersCount.data.count || 0;
        document.getElementById('total-items').textContent = itemsCount.data.count || 0;
        document.getElementById('pending-requests').textContent = pendingRequests.data.count || 0;
        document.getElementById('today-new').textContent = todayStats.data.new_items || 0;
    })
    .catch(error => {
        console.error('Failed to load dashboard data:', error);
    });
    
    // 加载图表数据
    loadDashboardCharts();
}

// 加载仪表盘图表
function loadDashboardCharts() {
    // 销毁现有图表实例
    if (userChart) {
        userChart.destroy();
        userChart = null;
    }
    if (categoryChart) {
        categoryChart.destroy();
        categoryChart = null;
    }
    
    // 用户注册趋势图
    apiRequest('/user-registration-trend')
        .then(response => {
            const data = response.data || [];
            const labels = data.map(item => item.date);
            const values = data.map(item => item.count);
            
            const ctx = document.getElementById('userChart').getContext('2d');
            if (userChart) {
                userChart.destroy();
            }
            userChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: '新注册用户',
                        data: values,
                        borderColor: '#4e73df',
                        backgroundColor: 'rgba(78, 115, 223, 0.1)',
                        tension: 0.3
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                }
            });
        })
        .catch(error => {
            console.error('Failed to load user chart:', error);
        });
    
    // 物品分类分布图
    apiRequest('/item-category-distribution')
        .then(response => {
            const data = response.data || [];
            const labels = data.map(item => item.category);
            const values = data.map(item => item.count);
            
            const ctx = document.getElementById('categoryChart').getContext('2d');
            if (categoryChart) {
                categoryChart.destroy();
            }
            categoryChart = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: labels,
                    datasets: [{
                        data: values,
                        backgroundColor: [
                            '#4e73df',
                            '#1cc88a',
                            '#36b9cc',
                            '#f6c23e',
                            '#e74a3b',
                            '#858796'
                        ]
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false
                }
            });
        })
        .catch(error => {
            console.error('Failed to load category chart:', error);
        });
}

// 加载用户数据
function loadUsers(page = 1, search = '', filter = '') {
    const params = new URLSearchParams({
        page: page,
        per_page: pageSize
    });
    
    if (search) params.append('search', search);
    if (filter) params.append('role', filter);
    
    apiRequest(`/users?${params}`)
        .then(response => {
            const data = response.data || {};
            displayUsers(data.users || []);
            updatePagination('users', data.pagination || {});
        })
        .catch(error => {
            console.error('Failed to load users:', error);
            displayUsers([]);
        });
}

// 显示用户数据
function displayUsers(users) {
    const tbody = document.getElementById('users-table-body');
    
    if (users.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="8" class="text-center py-4">
                    <div class="empty-state">
                        <i class="fas fa-users"></i>
                        <h5>暂无用户数据</h5>
                        <p>系统中还没有用户信息</p>
                    </div>
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = users.map(user => `
        <tr>
            <td>${user.user_id}</td>
            <td>${user.username}</td>
            <td>${user.email}</td>
            <td>${user.phone || '-'}</td>
            <td>
                <div class="rating-stars">
                    ${generateStars(user.reputation_score || 0)}
                    <span class="ms-1">${(user.reputation_score || 0).toFixed(1)}</span>
                </div>
            </td>
            <td>
                <span class="badge ${user.is_admin ? 'bg-danger' : 'bg-primary'}">
                    ${user.is_admin ? '管理员' : '普通用户'}
                </span>
            </td>
            <td>${formatDateTime(user.created_at)}</td>
            <td>
                <button class="btn btn-sm btn-outline-primary" onclick="showUserDetail(${user.user_id})">
                    <i class="fas fa-eye"></i>
                </button>
                ${!user.is_admin ? `
                    <button class="btn btn-sm btn-outline-warning ms-1" onclick="toggleUserStatus(${user.user_id})">
                        <i class="fas fa-ban"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-danger ms-1" onclick="deleteUser(${user.user_id}, '${user.username}')">
                        <i class="fas fa-trash"></i>
                    </button>
                ` : ''}
            </td>
        </tr>
    `).join('');
}

// 加载物品数据
function loadItems(page = 1, search = '', statusFilter = '', categoryFilter = '') {
    const params = new URLSearchParams({
        page: page,
        per_page: pageSize
    });
    
    if (search) params.append('search', search);
    if (statusFilter) params.append('status', statusFilter);
    if (categoryFilter) params.append('category_id', categoryFilter);
    
    apiRequest(`/items?${params}`)
        .then(response => {
            const data = response.data || {};
            displayItems(data.items || []);
            updatePagination('items', data.pagination || {});
        })
        .catch(error => {
            console.error('Failed to load items:', error);
            displayItems([]);
        });
}

// 显示物品数据
function displayItems(items) {
    const tbody = document.getElementById('items-table-body');
    
    if (items.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="8" class="text-center py-4">
                    <div class="empty-state">
                        <i class="fas fa-box"></i>
                        <h5>暂无物品数据</h5>
                        <p>系统中还没有物品信息</p>
                    </div>
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = items.map(item => `
        <tr>
            <td>${item.item_id}</td>
            <td>
                <div class="d-flex align-items-center">
                    ${item.images && item.images.length > 0 ? 
                        `<img src="${item.images[0].image_url}" alt="${item.title}" class="me-2" style="width: 40px; height: 40px; object-fit: cover; border-radius: 4px;" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';"><div class="me-2" style="width: 40px; height: 40px; background-color: #f8f9fc; border-radius: 4px; display: none; align-items: center; justify-content: center;"><i class="fas fa-image text-muted"></i></div>` : 
                        '<div class="me-2" style="width: 40px; height: 40px; background-color: #f8f9fc; border-radius: 4px; display: flex; align-items: center; justify-content: center;"><i class="fas fa-image text-muted"></i></div>'
                    }
                    <span>${item.title}</span>
                </div>
            </td>
            <td>${item.owner_username || '-'}</td>
            <td>${item.category_name || '-'}</td>
            <td>
                <span class="status-badge status-${item.status}">
                    ${getStatusText(item.status)}
                </span>
            </td>
            <td>${getConditionText(item.condition)}</td>
            <td>${formatDateTime(item.created_at)}</td>
            <td>
                <button class="btn btn-sm btn-outline-primary" onclick="showItemDetail(${item.item_id})">
                    <i class="fas fa-eye"></i>
                </button>
                <button class="btn btn-sm btn-outline-danger ms-1" onclick="deleteItem(${item.item_id})">
                    <i class="fas fa-trash"></i>
                </button>
            </td>
        </tr>
    `).join('');
}

// 加载分类数据
function loadCategories() {
    apiRequest('/categories/tree')
        .then(response => {
            const data = response.data || [];
            if (currentSection === 'categories') {
                displayCategories(data);
            }
            
            // 更新筛选器选项
            updateCategoryFilters(data);
        })
        .catch(error => {
            console.error('Failed to load categories:', error);
            if (currentSection === 'categories') {
                displayCategories([]);
            }
        });
}

// 显示分类数据
function displayCategories(categories) {
    const container = document.getElementById('categories-tree');
    
    if (categories.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-tags"></i>
                <h5>暂无分类数据</h5>
                <p>系统中还没有分类信息</p>
            </div>
        `;
        return;
    }
    
    // 直接渲染分类树（API已返回树结构）
    container.innerHTML = renderCategoryTree(categories);
}



// 渲染分类树
function renderCategoryTree(tree) {
    return tree.map(category => `
        <div class="category-item parent">
            <div class="d-flex justify-content-between align-items-center">
                <span>
                    <i class="fas fa-folder me-2"></i>
                    ${category.name} <small class="text-muted">(${category.item_count || 0}个物品)</small>
                </span>
                <div>
                    <button class="btn btn-sm btn-outline-light" onclick="editCategory(${category.category_id})">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-light ms-1" onclick="deleteCategory(${category.category_id})">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
            ${category.children && category.children.length > 0 ? `
                <div class="mt-2">
                    ${category.children.map(child => `
                        <div class="category-item child">
                            <div class="d-flex justify-content-between align-items-center">
                                <span>
                                    <i class="fas fa-file me-2"></i>
                                    ${child.name} <small class="text-muted">(${child.item_count || 0}个物品)</small>
                                </span>
                                <div>
                                    <button class="btn btn-sm btn-outline-primary" onclick="editCategory(${child.category_id})">
                                        <i class="fas fa-edit"></i>
                                    </button>
                                    <button class="btn btn-sm btn-outline-danger ms-1" onclick="deleteCategory(${child.category_id})">
                                        <i class="fas fa-trash"></i>
                                    </button>
                                </div>
                            </div>
                        </div>
                    `).join('')}
                </div>
            ` : ''}
        </div>
    `).join('');
}

// 更新分类筛选器
function updateCategoryFilters(categories) {
    const itemCategoryFilter = document.getElementById('item-category-filter');
    const parentCategorySelect = document.getElementById('parentCategory');
    
    // 扁平化分类数据
    const flatCategories = flattenCategories(categories);
    
    if (itemCategoryFilter) {
        const currentValue = itemCategoryFilter.value;
        itemCategoryFilter.innerHTML = '<option value="">全部分类</option>' +
            flatCategories.map(cat => `<option value="${cat.id}">${cat.name}</option>`).join('');
        itemCategoryFilter.value = currentValue;
    }
    
    if (parentCategorySelect) {
        parentCategorySelect.innerHTML = '<option value="">无（顶级分类）</option>' +
            categories.map(cat => `<option value="${cat.id}">${cat.name}</option>`).join('');
    }
}

// 扁平化分类树
function flattenCategories(categories) {
    const result = [];
    
    function flatten(cats, prefix = '') {
        cats.forEach(cat => {
            result.push({
                id: cat.category_id,
                name: prefix + cat.name
            });
            
            if (cat.children && cat.children.length > 0) {
                flatten(cat.children, prefix + cat.name + ' > ');
            }
        });
    }
    
    flatten(categories);
    return result;
}

// 加载交易请求数据
function loadRequests(page = 1, statusFilter = '') {
    const params = new URLSearchParams({
        page: page,
        per_page: pageSize
    });
    
    if (statusFilter) params.append('status', statusFilter);
    
    apiRequest(`/requests?${params}`)
        .then(response => {
            const data = response.data || {};
            displayRequests(data.requests || []);
            updatePagination('requests', data.pagination || {});
        })
        .catch(error => {
            console.error('Failed to load requests:', error);
            displayRequests([]);
        });
}

// 显示交易请求数据
function displayRequests(requests) {
    const tbody = document.getElementById('requests-table-body');
    
    if (requests.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="text-center py-4">
                    <div class="empty-state">
                        <i class="fas fa-handshake"></i>
                        <h5>暂无交易请求</h5>
                        <p>系统中还没有交易请求</p>
                    </div>
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = requests.map(request => `
        <tr>
            <td>${request.id}</td>
            <td>${request.item_title || '-'}</td>
            <td>${request.requester_username || '-'}</td>
            <td>${request.owner_username || '-'}</td>
            <td>
                <span class="status-badge status-${request.status}">
                    ${getRequestStatusText(request.status)}
                </span>
            </td>
            <td>${formatDateTime(request.created_at)}</td>
            <td>
                <div class="btn-group" role="group">
                    <button class="btn btn-sm btn-outline-primary" onclick="showRequestDetail(${request.id})" title="查看详情">
                        <i class="fas fa-eye"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-success" onclick="editRequestFromList(${request.id})" title="编辑">
                        <i class="fas fa-edit"></i>
                    </button>
                    <div class="btn-group" role="group">
                        <button class="btn btn-sm btn-outline-warning dropdown-toggle" data-bs-toggle="dropdown" title="更改状态">
                            <i class="fas fa-exchange-alt"></i>
                        </button>
                        <ul class="dropdown-menu">
                            <li><a class="dropdown-item" href="#" onclick="changeRequestStatus(${request.id}, 'pending')">待处理</a></li>
                            <li><a class="dropdown-item" href="#" onclick="changeRequestStatus(${request.id}, 'accepted')">已接受</a></li>
                            <li><a class="dropdown-item" href="#" onclick="changeRequestStatus(${request.id}, 'rejected')">已拒绝</a></li>
                            <li><a class="dropdown-item" href="#" onclick="changeRequestStatus(${request.id}, 'cancelled')">已取消</a></li>
                            <li><a class="dropdown-item" href="#" onclick="changeRequestStatus(${request.id}, 'completed')">已完成</a></li>
                        </ul>
                    </div>
                    <button class="btn btn-sm btn-outline-danger" onclick="deleteRequest(${request.id})" title="删除">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </td>
        </tr>
    `).join('');
}

// 加载评价数据
function loadReviews(page = 1, ratingFilter = '') {
    const params = new URLSearchParams({
        page: page,
        per_page: pageSize
    });
    
    if (ratingFilter) params.append('rating', ratingFilter);
    
    apiRequest(`/reviews?${params}`)
        .then(data => {
            displayReviews(data.data.reviews || []);
            updatePagination('reviews', data.data.pagination || {});
        })
        .catch(error => {
            console.error('Failed to load reviews:', error);
            displayReviews([]);
        });
}

// 显示评价数据
function displayReviews(reviews) {
    const tbody = document.getElementById('reviews-table-body');
    
    if (reviews.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="text-center py-4">
                    <div class="empty-state">
                        <i class="fas fa-star"></i>
                        <h5>暂无评价数据</h5>
                        <p>系统中还没有评价信息</p>
                    </div>
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = reviews.map(review => `
        <tr>
            <td>${review.id}</td>
            <td>${review.reviewer_username || '-'}</td>
            <td>${review.reviewee_username || '-'}</td>
            <td>
                <div class="rating-stars">
                    ${generateStars(review.rating)}
                </div>
            </td>
            <td>
                <div style="max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${review.comment || ''}">
                    ${review.comment || '-'}
                </div>
            </td>
            <td>${formatDateTime(review.created_at)}</td>
            <td>
                <button class="btn btn-sm btn-outline-danger" onclick="deleteReview(${review.id})">
                    <i class="fas fa-trash"></i>
                </button>
            </td>
        </tr>
    `).join('');
}

// 加载消息数据
function loadMessages(page = 1, typeFilter = '', readFilter = '') {
    const params = new URLSearchParams({
        page: page,
        per_page: pageSize
    });
    
    if (typeFilter) params.append('type', typeFilter);
    if (readFilter) params.append('is_read', readFilter);
    
    apiRequest(`/messages?${params}`)
        .then(response => {
            const data = response.data || {};
            displayMessages(data.items || []);
            updatePagination('messages', data.pagination || {});
        })
        .catch(error => {
            console.error('Failed to load messages:', error);
            displayMessages([]);
        });
}

// 显示消息数据
function displayMessages(messages) {
    const tbody = document.getElementById('messages-table-body');
    
    if (messages.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="8" class="text-center py-4">
                    <div class="empty-state">
                        <i class="fas fa-envelope"></i>
                        <h5>暂无消息数据</h5>
                        <p>系统中还没有消息信息</p>
                    </div>
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = messages.map(message => `
        <tr>
            <td>${message.message_id}</td>
            <td>${message.sender_username || '系统'}</td>
            <td>${message.recipient_username || '-'}</td>
            <td>
                <span class="badge bg-info">
                    ${getMessageTypeText(message.type)}
                </span>
            </td>
            <td>
                <div style="max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${message.content || ''}">
                    ${message.content || '-'}
                </div>
            </td>
            <td>
                <span class="badge ${message.is_read ? 'bg-success' : 'bg-warning'}">
                    ${message.is_read ? '已读' : '未读'}
                </span>
            </td>
            <td>${formatDateTime(message.created_at)}</td>
            <td>
                <button class="btn btn-sm btn-outline-danger" onclick="deleteMessage(${message.message_id})">
                    <i class="fas fa-trash"></i>
                </button>
            </td>
        </tr>
    `).join('');
}



// 更新分页
function updatePagination(section, pagination) {
    const paginationContainer = document.getElementById(`${section}-pagination`);
    if (!paginationContainer || !pagination.pages) {
        return;
    }
    
    const pageNum = pagination.page || 1;
    const totalPages = pagination.pages;
    
    let paginationHTML = '';
    
    // 上一页
    if (pageNum > 1) {
        paginationHTML += `
            <li class="page-item">
                <a class="page-link" href="#" onclick="changePage('${section}', ${pageNum - 1})">
                    <i class="fas fa-chevron-left"></i>
                </a>
            </li>
        `;
    }
    
    // 页码
    const startPage = Math.max(1, pageNum - 2);
    const endPage = Math.min(totalPages, pageNum + 2);
    
    for (let i = startPage; i <= endPage; i++) {
        paginationHTML += `
            <li class="page-item ${i === pageNum ? 'active' : ''}">
                <a class="page-link" href="#" onclick="changePage('${section}', ${i})">${i}</a>
            </li>
        `;
    }
    
    // 下一页
    if (pageNum < totalPages) {
        paginationHTML += `
            <li class="page-item">
                <a class="page-link" href="#" onclick="changePage('${section}', ${pageNum + 1})">
                    <i class="fas fa-chevron-right"></i>
                </a>
            </li>
        `;
    }
    
    paginationContainer.innerHTML = paginationHTML;
}

// 切换页面
function changePage(section, page) {
    currentPage = page;
    
    switch(section) {
        case 'users':
            const userSearch = document.getElementById('user-search').value;
            const userFilter = document.getElementById('user-filter').value;
            loadUsers(page, userSearch, userFilter);
            break;
        case 'items':
            const itemSearch = document.getElementById('item-search').value;
            const itemStatusFilter = document.getElementById('item-status-filter').value;
            const itemCategoryFilter = document.getElementById('item-category-filter').value;
            loadItems(page, itemSearch, itemStatusFilter, itemCategoryFilter);
            break;
        case 'requests':
            const requestStatusFilter = document.getElementById('request-status-filter').value;
            loadRequests(page, requestStatusFilter);
            break;
        case 'reviews':
            const reviewRatingFilter = document.getElementById('review-rating-filter').value;
            loadReviews(page, reviewRatingFilter);
            break;
        case 'messages':
            const messageTypeFilter = document.getElementById('message-type-filter').value;
            const messageReadFilter = document.getElementById('message-read-filter').value;
            loadMessages(page, messageTypeFilter, messageReadFilter);
            break;
    }
}

// 搜索和筛选函数
function searchUsers() {
    const search = document.getElementById('user-search').value;
    const filter = document.getElementById('user-filter').value;
    loadUsers(1, search, filter);
}

function filterUsers() {
    const search = document.getElementById('user-search').value;
    const filter = document.getElementById('user-filter').value;
    loadUsers(1, search, filter);
}

function searchItems() {
    const search = document.getElementById('item-search').value;
    const statusFilter = document.getElementById('item-status-filter').value;
    const categoryFilter = document.getElementById('item-category-filter').value;
    loadItems(1, search, statusFilter, categoryFilter);
}

function filterItems() {
    const search = document.getElementById('item-search').value;
    const statusFilter = document.getElementById('item-status-filter').value;
    const categoryFilter = document.getElementById('item-category-filter').value;
    loadItems(1, search, statusFilter, categoryFilter);
}

function filterRequests() {
    const statusFilter = document.getElementById('request-status-filter').value;
    loadRequests(1, statusFilter);
}

function filterReviews() {
    const ratingFilter = document.getElementById('review-rating-filter').value;
    loadReviews(1, ratingFilter);
}

function filterMessages() {
    const typeFilter = document.getElementById('message-type-filter').value;
    const readFilter = document.getElementById('message-read-filter').value;
    loadMessages(1, typeFilter, readFilter);
}

// 刷新函数
function refreshUsers() {
    loadUsers();
}

function refreshItems() {
    loadItems();
    loadCategories();
}

function refreshCategories() {
    loadCategories();
}

function refreshRequests() {
    loadRequests();
}

function refreshReviews() {
    loadReviews();
}

function refreshMessages() {
    loadMessages();
}

// 工具函数
function formatDateTime(dateString) {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleString('zh-CN');
}

function generateStars(rating) {
    const fullStars = Math.floor(rating);
    const hasHalfStar = rating % 1 >= 0.5;
    const emptyStars = 5 - fullStars - (hasHalfStar ? 1 : 0);
    
    let stars = '';
    
    for (let i = 0; i < fullStars; i++) {
        stars += '<i class="fas fa-star"></i>';
    }
    
    if (hasHalfStar) {
        stars += '<i class="fas fa-star-half-alt"></i>';
    }
    
    for (let i = 0; i < emptyStars; i++) {
        stars += '<i class="far fa-star"></i>';
    }
    
    return stars;
}

function getStatusText(status) {
    const statusMap = {
        'available': '可用',
        'pending': '待处理',
        'completed': '已完成',
        'removed': '已下架',
        'reserved': '已预订',
        'completed': '已完成',
        'cancelled': '已取消'
    };
    return statusMap[status] || status;
}

function getRequestStatusText(status) {
    const statusMap = {
        'pending': '待处理',
        'accepted': '已接受',
        'rejected': '已拒绝',
        'cancelled': '已取消'
    };
    return statusMap[status] || status;
}

function getConditionText(condition) {
    const conditionMap = {
        'new': '全新',
        'like_new': '几乎全新',
        'good': '良好',
        'fair': '一般',
        'poor': '较差'
    };
    return conditionMap[condition] || condition;
}

function getMessageTypeText(type) {
    const typeMap = {
        'request_notification': '请求通知',
        'status_update': '状态更新',
        'system_announcement': '系统公告',
        'chat_message': '聊天消息'
    };
    return typeMap[type] || type;
}

// 详情显示函数
function showUserDetail(userId) {
    apiRequest(`/users/${userId}`)
        .then(user => {
            const modal = new bootstrap.Modal(document.getElementById('userDetailModal'));
            console.log(user)
            document.getElementById('userDetailContent').innerHTML = `
                <div class="row">
                    <div class="col-md-6">
                        <h6>基本信息</h6>
                        <p><strong>用户名:</strong> ${user.data.username}</p>
                        <p><strong>邮箱:</strong> ${user.data.email}</p>
                        <p><strong>手机号:</strong> ${user.data.phone || '-'}</p>
                        <p><strong>地址:</strong> ${user.data.address || '-'}</p>
                        <p><strong>角色:</strong> ${user.data.is_admin ? '管理员' : '普通用户'}</p>
                    </div>
                    <div class="col-md-6">
                        <h6>统计信息</h6>
                        <p><strong>信誉评分:</strong> 
                            <div class="rating-stars">
                                ${generateStars(user.data.reputation_score || 0)}
                                <span class="ms-1">${(user.data.reputation_score || 0).toFixed(1)}</span>
                            </div>
                        </p>
                        <p><strong>发布物品数:</strong> ${user.data.items_count || 0}</p>
                        <p><strong>交易次数:</strong> ${user.data.transactions_count || 0}</p>
                        <p><strong>注册时间:</strong> ${formatDateTime(user.data.created_at)}</p>
                        <p><strong>最后登录:</strong> ${formatDateTime(user.data.last_login)}</p>
                    </div>
                </div>
            `;
            modal.show();
        })
        .catch(error => {
            console.error('Failed to load user detail:', error);
        });
}

// 全局变量存储当前查看的物品数据
let currentItemData = null;

function showItemDetail(itemId) {
    apiRequest(`/items/${itemId}`)
        .then(item => {
            // 存储当前物品数据
            currentItemData = item;
            console.log(item)
            const modal = new bootstrap.Modal(document.getElementById('itemDetailModal'));
            document.getElementById('itemDetailContent').innerHTML = `
                <div class="row">
                    <div class="col-md-6">
                        <h6>物品信息</h6>
                        <p><strong>物品ID:</strong> ${item.data.item_id || '-'}</p>
                        <p><strong>标题:</strong> ${item.data.title || '-'}</p>
                        <p><strong>描述:</strong> ${item.data.description || '-'}</p>
                        <p><strong>分类:</strong> ${item.data.category_name || '-'}</p>
                        <p><strong>状态:</strong> 
                            <span class="status-badge status-${item.data.status}">
                                ${getStatusText(item.data.status)}
                            </span>
                        </p>
                        <p><strong>新旧程度:</strong> ${getConditionText(item.data.condition)}</p>
                        <p><strong>发布者:</strong> ${item.data.owner_username || '-'}</p>
                    </div>
                    <div class="col-md-6">
                        <h6>其他信息</h6>
                        <p><strong>发布时间:</strong> ${formatDateTime(item.data.created_at)}</p>
                        <p><strong>更新时间:</strong> ${formatDateTime(item.data.updated_at)}</p>
                        ${item.latitude && item.data.longitude ? `
                            <p><strong>位置:</strong> ${item.data.latitude}, ${item.data.longitude}</p>
                        ` : ''}
                        ${item.data.images && item.data.images.length > 0 ? `
                            <div>
                                <strong>图片:</strong>
                                <div class="mt-2">
                                    ${item.data.images.map(img => `
                                        <img src="${img.image_url}" alt="物品图片" class="me-2 mb-2" style="width: 80px; height: 80px; object-fit: cover; border-radius: 4px; cursor: pointer;" onerror="this.style.display='none';" onclick="showImagePreview('${img.image_url}')">
                                    `).join('')}
                                </div>
                            </div>
                        ` : '<p><strong>图片:</strong> 暂无图片</p>'}
                    </div>
                </div>
            `;
            modal.show();
        })
        .catch(error => {
            console.error('Failed to load item detail:', error);
            showAlert('获取物品详情失败', 'error');
        });
}

// 显示编辑物品模态框
function showEditItemModal() {
    console.log('showEditItemModal called, currentItemData:', currentItemData);
    if (!currentItemData) {
        showAlert('请先选择要编辑的物品', 'error');
        return;
    }
    console.log('currentItemData.data:', currentItemData.data);
    console.log('item_id:', currentItemData.data ? currentItemData.data.item_id : 'data is null');
    
    // 关闭详情模态框
    const detailModal = bootstrap.Modal.getInstance(document.getElementById('itemDetailModal'));
    if (detailModal) {
        detailModal.hide();
    }
    
    // 加载分类和用户数据
    Promise.all([
        apiRequest('/categories/tree'),
        apiRequest('/users')
    ]).then(([categoriesResponse, usersResponse]) => {
        const categories = categoriesResponse.data || [];
        const users = usersResponse.data?.users || [];
        
        // 填充分类选项
        const categorySelect = document.getElementById('editItemCategory');
        categorySelect.innerHTML = '<option value="">请选择分类</option>';
        categories.forEach(category => {
            categorySelect.innerHTML += `<option value="${category.category_id}">${category.name}</option>`;
            if (category.children && category.children.length > 0) {
                category.children.forEach(child => {
                    categorySelect.innerHTML += `<option value="${child.category_id}">　├ ${child.name}</option>`;
                });
            }
        });
        
        // 填充用户选项
        const userSelect = document.getElementById('editItemOwner');
        userSelect.innerHTML = '<option value="">请选择所有者</option>';
        users.forEach(user => {
            userSelect.innerHTML += `<option value="${user.user_id}">${user.username}</option>`;
        });
        
        // 填充表单数据
        const itemId = currentItemData.data && currentItemData.data.item_id ? currentItemData.data.item_id : null;
        if (!itemId) {
            console.error('物品ID为空:', currentItemData);
            showAlert('无法获取物品ID，请重新选择物品', 'error');
            return;
        }
        document.getElementById('editItemId').value = itemId;
        console.log('设置editItemId为:', itemId);
        document.getElementById('editItemTitle').value = currentItemData.data.title || '';
        document.getElementById('editItemDescription').value = currentItemData.data.description || '';
        document.getElementById('editItemCategory').value = currentItemData.data.category_id || '';
        document.getElementById('editItemStatus').value = currentItemData.data.status || '';
        document.getElementById('editItemCondition').value = currentItemData.data.condition || '';
        document.getElementById('editItemOwner').value = currentItemData.data.user_id || '';
        
        // 显示当前图片
        const currentImagesDiv = document.getElementById('currentImages');
        if (currentItemData.data.images && currentItemData.data.images.length > 0) {
            currentImagesDiv.innerHTML = currentItemData.data.images.map(img => `
                <div class="d-inline-block position-relative me-2 mb-2">
                    <img src="${img.image_url}" alt="物品图片" class="current-image" data-image-url="${img.image_url}" data-image-id="${img.image_id}" style="width: 80px; height: 80px; object-fit: cover; border-radius: 4px; cursor: pointer;" onerror="this.style.display='none';" onclick="showImagePreview('${img.image_url}')">
                    <button type="button" class="btn btn-sm btn-danger position-absolute top-0 end-0" style="padding: 2px 6px; font-size: 12px;" onclick="removeImageFromEdit(${img.image_id})" title="删除图片">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            `).join('');
        } else {
            currentImagesDiv.innerHTML = '<p class="text-muted">暂无图片</p>';
        }
        
        // 显示编辑模态框
        const editModal = new bootstrap.Modal(document.getElementById('editItemModal'));
        editModal.show();
        
    }).catch(error => {
        console.error('Failed to load edit data:', error);
        showAlert('加载编辑数据失败', 'error');
    });
}

// 更新物品
async function updateItem() {
    const itemId = document.getElementById('editItemId').value;
    console.log('editItemId value:', itemId);
    console.log('currentItemData:', currentItemData);
    const title = document.getElementById('editItemTitle').value.trim();
    const description = document.getElementById('editItemDescription').value.trim();
    const categoryId = document.getElementById('editItemCategory').value;
    const status = document.getElementById('editItemStatus').value;
    const condition = document.getElementById('editItemCondition').value;
    const ownerId = document.getElementById('editItemOwner').value;
    const imageFiles = document.getElementById('editItemImages').files;
    
    // 验证必填字段
    if (!title || !description || !categoryId || !status || !condition || !ownerId) {
        showAlert('请填写所有必填字段', 'error');
        return;
    }
    
    try {
        // 获取当前保留的图片URLs
        const currentImages = Array.from(document.querySelectorAll('#currentImages .current-image'))
            .map(img => img.dataset.imageUrl);
        
        // 上传新图片
        let newImageUrls = [];
        if (imageFiles.length > 0) {
            for (let file of imageFiles) {
                const formData = new FormData();
                formData.append('image', file);
                
                const uploadResponse = await fetch(`${API_BASE_URL}/upload/image`, {
                    method: 'POST',
                    body: formData
                });
                
                if (!uploadResponse.ok) {
                    const errorData = await uploadResponse.json();
                    throw new Error(`上传失败: ${errorData.message || '未知错误'}`);
                }
                
                const uploadData = await uploadResponse.json();
                newImageUrls.push(uploadData.data.image_url);
            }
        }
        
        // 合并现有图片和新图片
        const allImageUrls = [...currentImages, ...newImageUrls];
        
        // 验证至少有一张图片
        if (allImageUrls.length === 0) {
            showAlert('至少需要一张图片', 'error');
            return;
        }
        
        // 更新物品信息
        const updateData = {
            title: title,
            description: description,
            category_id: parseInt(categoryId),
            status: status,
            condition: condition,
            user_id: parseInt(ownerId),
            image_urls: allImageUrls
        };
        
        const response = await fetch(`${API_BASE_URL}/items/${itemId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(updateData)
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.message || '更新失败');
        }
        
        showAlert('物品更新成功', 'success');
        
        // 关闭编辑模态框
        const editModal = bootstrap.Modal.getInstance(document.getElementById('editItemModal'));
        if (editModal) {
            editModal.hide();
        }
        
        // 刷新物品列表
        refreshItems();
        
        // 重新加载物品详情
        showItemDetail(itemId);
        
    } catch (error) {
        console.error('Failed to update item:', error);
        showAlert(`更新物品失败: ${error.message}`, 'error');
    }
}

// 删除图片
function removeImage(imageId) {
    if (confirm('确定要删除这张图片吗？')) {
        apiRequest(`/items/images/${imageId}`, {
            method: 'DELETE'
        })
        .then(() => {
            showAlert('图片删除成功', 'success');
            // 重新加载当前物品数据
            if (currentItemData) {
                showItemDetail(currentItemData.data.item_id);
            }
        })
        .catch(error => {
            console.error('Failed to delete image:', error);
            showAlert('删除图片失败', 'error');
        });
    }
}

// 在编辑模式下删除图片（仅从界面移除，不立即删除数据库记录）
function removeImageFromEdit(imageId) {
    if (confirm('确定要删除这张图片吗？')) {
        // 从界面中移除图片元素
        const imageElement = document.querySelector(`[data-image-id="${imageId}"]`);
        if (imageElement) {
            imageElement.closest('.d-inline-block').remove();
        }
        
        // 检查是否还有图片
        const remainingImages = document.querySelectorAll('#currentImages .current-image');
        if (remainingImages.length === 0) {
            document.getElementById('currentImages').innerHTML = '<p class="text-muted">暂无图片</p>';
        }
    }
}

// 图片预览功能
function showImagePreview(imageUrl) {
    const modal = document.createElement('div');
    modal.className = 'modal fade';
    modal.innerHTML = `
        <div class="modal-dialog modal-lg modal-dialog-centered">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">图片预览</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body text-center">
                    <img src="${imageUrl}" alt="图片预览" style="max-width: 100%; max-height: 70vh; object-fit: contain;">
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    const previewModal = new bootstrap.Modal(modal);
    previewModal.show();
    
    // 模态框关闭后移除元素
    modal.addEventListener('hidden.bs.modal', () => {
        document.body.removeChild(modal);
    });
}

function showRequestDetail(requestId) {
    apiRequest(`/requests/${requestId}`)
        .then(response => {
            const request = response.data;
            alert(`请求详情:\n请求ID: ${request.id}\n物品: ${request.item_title}\n请求者: ${request.requester_username}\n状态: ${getRequestStatusText(request.status)}\n时间: ${formatDateTime(request.created_at)}`);
        })
        .catch(error => {
            console.error('Failed to load request detail:', error);
            showAlert('获取请求详情失败', 'error');
        });
}

// 操作函数
function toggleUserStatus(userId) {
    if (confirm('确定要切换用户状态吗？')) {
        apiRequest(`/users/${userId}/toggle-status`, {
            method: 'POST'
        })
        .then(() => {
            showAlert('用户状态已更新', 'success');
            refreshUsers();
        })
        .catch(error => {
            console.error('Failed to toggle user status:', error);
        });
    }
}

function deleteItem(itemId) {
    if (confirm('确定要删除这个物品吗？此操作不可恢复。')) {
        apiRequest(`/items/${itemId}`, {
            method: 'DELETE'
        })
        .then(() => {
            showAlert('物品已删除', 'success');
            refreshItems();
        })
        .catch(error => {
            console.error('Failed to delete item:', error);
            let errorMessage = '删除物品失败';
            if (error.message && error.message.includes('400')) {
                errorMessage = '该物品还有待处理的请求，无法删除';
            }
            showAlert(errorMessage, 'danger');
        });
    }
}

function deleteReview(reviewId) {
    if (confirm('确定要删除这条评价吗？此操作不可恢复。')) {
        apiRequest(`/reviews/${reviewId}`, {
            method: 'DELETE'
        })
        .then(() => {
            showAlert('评价已删除', 'success');
            refreshReviews();
        })
        .catch(error => {
            console.error('Failed to delete review:', error);
        });
    }
}

function deleteMessage(messageId) {
    if (confirm('确定要删除这条消息吗？此操作不可恢复。')) {
        apiRequest(`/messages/${messageId}`, {
            method: 'DELETE'
        })
        .then(() => {
            showAlert('消息已删除', 'success');
            refreshMessages();
        })
        .catch(error => {
            console.error('Failed to delete message:', error);
        });
    }
}

function deleteUser(userId, username) {
    if (confirm(`确定要删除用户 "${username}" 吗？\n\n此操作将会：\n- 删除该用户的所有物品\n- 删除该用户的所有评价\n- 删除该用户的所有消息\n- 删除该用户的所有交易请求\n\n此操作不可恢复！`)) {
        apiRequest(`/users/${userId}`, {
            method: 'DELETE'
        })
        .then(() => {
            showAlert(`用户 "${username}" 已成功删除`, 'success');
            refreshUsers();
        })
        .catch(error => {
            console.error('Failed to delete user:', error);
            let errorMessage = '删除用户失败';
            if (error.message) {
                if (error.message.includes('管理员')) {
                    errorMessage = '不能删除管理员用户';
                } else if (error.message.includes('未完成的交易')) {
                    errorMessage = '该用户还有未完成的交易，无法删除';
                } else if (error.message.includes('自己')) {
                    errorMessage = '不能删除自己的账户';
                } else {
                    errorMessage = error.message;
                }
            }
            showAlert(errorMessage, 'danger');
        });
    }
}

// 分类管理函数
function showAddCategoryModal() {
    // 加载父分类选项
    loadParentCategoriesForSelect();
    const modal = new bootstrap.Modal(document.getElementById('addCategoryModal'));
    modal.show();
}

function addCategory() {
    const name = document.getElementById('categoryName').value;
    const parentId = document.getElementById('parentCategory').value;
    
    if (!name.trim()) {
        showAlert('请输入分类名称', 'warning');
        return;
    }
    
    const data = { name: name.trim() };
    if (parentId) {
        data.parent_id = parseInt(parentId);
    }
    
    apiRequest('/categories', {
        method: 'POST',
        body: JSON.stringify(data)
    })
    .then(() => {
        showAlert('分类添加成功', 'success');
        const modal = bootstrap.Modal.getInstance(document.getElementById('addCategoryModal'));
        modal.hide();
        document.getElementById('addCategoryForm').reset();
        refreshCategories();
    })
    .catch(error => {
        console.error('Failed to add category:', error);
        showAlert('添加分类失败', 'danger');
    });
}

function editCategory(categoryId) {
    const newName = prompt('请输入新的分类名称:');
    if (newName && newName.trim()) {
        apiRequest(`/categories/${categoryId}`, {
            method: 'PUT',
            body: JSON.stringify({ name: newName.trim() })
        })
        .then(() => {
            showAlert('分类更新成功', 'success');
            refreshCategories();
        })
        .catch(error => {
            console.error('Failed to update category:', error);
            showAlert('更新分类失败', 'danger');
        });
    }
}

function deleteCategory(categoryId) {
    if (confirm('确定要删除这个分类吗？此操作将同时删除所有子分类。')) {
        apiRequest(`/categories/${categoryId}`, {
            method: 'DELETE'
        })
        .then(() => {
            showAlert('分类已删除', 'success');
            refreshCategories();
        })
        .catch(error => {
            console.error('Failed to delete category:', error);
            let errorMessage = '删除分类失败';
            if (error.message && error.message.includes('该分类下还有子分类')) {
                errorMessage = '该分类下还有子分类，无法删除';
            } else if (error.message && error.message.includes('该分类下还有物品')) {
                errorMessage = '该分类下还有物品，无法删除';
            }
            showAlert(errorMessage, 'danger');
        });
    }
}

// 显示添加用户模态框
function showAddUserModal() {
    const modal = new bootstrap.Modal(document.getElementById('addUserModal'));
    modal.show();
}

// 添加用户
function addUser() {
    const username = document.getElementById('userUsername').value.trim();
    const email = document.getElementById('userEmail').value.trim();
    const password = document.getElementById('userPassword').value;
    const phone = document.getElementById('userPhone').value.trim();
    const address = document.getElementById('userAddress').value.trim();
    const isAdmin = document.getElementById('userIsAdmin').checked;
    
    // 验证必填字段
    if (!username || !email || !password || !address) {
        showAlert('请填写所有必填字段', 'warning');
        return;
    }
    
    // 验证邮箱格式
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
        showAlert('请输入有效的邮箱地址', 'warning');
        return;
    }
    
    // 验证密码长度
    if (password.length < 6) {
        showAlert('密码长度至少6位', 'warning');
        return;
    }
    
    const userData = {
        username: username,
        email: email,
        password: password,
        address: address
    };
    
    if (phone) {
        userData.phone = phone;
    }
    
    if (isAdmin) {
        userData.is_admin = true;
    }
    
    apiRequest('/users/register', {
        method: 'POST',
        body: JSON.stringify(userData)
    })
    .then(() => {
        showAlert('用户添加成功', 'success');
        const modal = bootstrap.Modal.getInstance(document.getElementById('addUserModal'));
        modal.hide();
        document.getElementById('addUserForm').reset();
        refreshUsers();
    })
    .catch(error => {
        console.error('Failed to add user:', error);
        showAlert(error.message || '添加用户失败', 'danger');
    });
}

// 显示添加物品模态框
function showAddItemModal() {
    // 加载分类和用户选项
    loadCategoriesForSelect();
    loadUsersForSelect();
    
    const modal = new bootstrap.Modal(document.getElementById('addItemModal'));
    modal.show();
}

// 为选择框加载分类
function loadCategoriesForSelect() {
    apiRequest('/categories/tree')
        .then(response => {
            const categories = response.data || [];
            const select = document.getElementById('itemCategory');
            const flatCategories = flattenCategories(categories);
            
            select.innerHTML = '<option value="">请选择分类</option>' +
                flatCategories.map(cat => `<option value="${cat.id}">${cat.name}</option>`).join('');
        })
        .catch(error => {
            console.error('Failed to load categories for select:', error);
        });
}

// 为选择框加载用户
function loadUsersForSelect() {
    apiRequest('/users?per_page=1000')
        .then(response => {
            const users = response.data?.users || [];
            const select = document.getElementById('itemOwner');
            
            select.innerHTML = '<option value="">请选择所有者</option>' +
                users.map(user => `<option value="${user.user_id}">${user.username} (${user.email})</option>`).join('');
        })
        .catch(error => {
            console.error('Failed to load users for select:', error);
        });
}

// 为父分类选择框加载分类
function loadParentCategoriesForSelect() {
    apiRequest('/categories/tree')
        .then(response => {
            const categories = response.data || [];
            const select = document.getElementById('parentCategory');
            const flatCategories = flattenCategories(categories);
            
            select.innerHTML = '<option value="">无（顶级分类）</option>' +
                flatCategories.map(cat => `<option value="${cat.id}">${cat.name}</option>`).join('');
        })
        .catch(error => {
            console.error('Failed to load parent categories for select:', error);
        });
}

// 添加物品
async function addItem() {
    const title = document.getElementById('itemTitle').value.trim();
    const price = parseFloat(document.getElementById('itemPrice').value);
    const categoryId = parseInt(document.getElementById('itemCategory').value);
    const condition = document.getElementById('itemCondition').value;
    const description = document.getElementById('itemDescription').value.trim();
    const ownerId = parseInt(document.getElementById('itemOwner').value);
    const images = document.getElementById('itemImages').files;
    
    // 验证必填字段
    if (!title || !price || !categoryId || !condition || !description || !ownerId) {
        showAlert('请填写所有必填字段', 'warning');
        return;
    }
    
    if (price <= 0) {
        showAlert('价格必须大于0', 'warning');
        return;
    }
    
    if (images.length === 0) {
        showAlert('请至少上传一张图片', 'warning');
        return;
    }
    
    try {
        // 先上传图片
        const imageUrls = [];
        for (let i = 0; i < images.length; i++) {
            const formData = new FormData();
            formData.append('image', images[i]);
            
            const uploadResponse = await fetch(`${API_BASE_URL}/upload/image`, {
                method: 'POST',
                body: formData
            });
            
            if (!uploadResponse.ok) {
                const errorData = await uploadResponse.json();
                throw new Error(errorData.message || '图片上传失败');
            }
            
            const uploadResult = await uploadResponse.json();
            imageUrls.push(uploadResult.data.image_url);
        }
        
        // 创建物品
        const itemData = {
            title: title,
            description: description,
            category_id: categoryId,
            condition: condition,
            image_urls: imageUrls
        };
        
        const response = await fetch(`${API_BASE_URL}/items`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(itemData)
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
        }
        
        showAlert('物品添加成功', 'success');
        const modal = bootstrap.Modal.getInstance(document.getElementById('addItemModal'));
        modal.hide();
        document.getElementById('addItemForm').reset();
        refreshItems();
        
    } catch (error) {
        console.error('Failed to add item:', error);
        showAlert(error.message || '添加物品失败', 'danger');
    }
}

// ==================== 交易请求管理功能 ====================

// 显示新增交易请求模态框
function showAddRequestModal() {
    // 清空表单
    document.getElementById('addRequestForm').reset();
    
    // 加载物品和用户选项
    loadItemsForRequest();
    loadUsersForRequest();
    
    // 显示模态框
    const modal = new bootstrap.Modal(document.getElementById('addRequestModal'));
    modal.show();
}

// 为请求加载可用物品
function loadItemsForRequest() {
    apiRequest('/items?status=available&per_page=100')
        .then(response => {
            const items = response.data?.items || [];
            const select = document.getElementById('requestItem');
            
            select.innerHTML = '<option value="">请选择物品</option>';
            items.forEach(item => {
                select.innerHTML += `<option value="${item.item_id}">${item.title} (${item.owner_username})</option>`;
            });
        })
        .catch(error => {
            console.error('Failed to load items:', error);
        });
}

// 为请求加载用户
function loadUsersForRequest() {
    apiRequest('/users?per_page=100')
        .then(response => {
            const users = response.data?.users || [];
            const select = document.getElementById('requestRequester');
            
            select.innerHTML = '<option value="">请选择请求者</option>';
            users.forEach(user => {
                select.innerHTML += `<option value="${user.user_id}">${user.username}</option>`;
            });
        })
        .catch(error => {
            console.error('Failed to load users:', error);
        });
}

// 创建新的交易请求
async function addRequest() {
    try {
        const itemId = document.getElementById('requestItem').value;
        const requesterId = document.getElementById('requestRequester').value;
        const message = document.getElementById('requestMessage').value.trim();
        const status = document.getElementById('requestStatus').value;
        
        if (!itemId || !requesterId) {
            showAlert('请选择物品和请求者', 'warning');
            return;
        }
        
        const requestData = {
            item_id: parseInt(itemId),
            requester_id: parseInt(requesterId),
            message: message || null,
            status: status
        };
        
        // 如果是管理员创建，需要特殊处理
        const response = await apiRequest('/requests/admin', {
            method: 'POST',
            body: JSON.stringify(requestData)
        });
        
        showAlert('交易请求创建成功', 'success');
        
        // 关闭模态框
        const modal = bootstrap.Modal.getInstance(document.getElementById('addRequestModal'));
        modal.hide();
        
        // 刷新列表
        loadRequests();
        
    } catch (error) {
        console.error('Failed to create request:', error);
        showAlert('创建交易请求失败: ' + error.message, 'danger');
    }
}

// 从列表直接编辑请求
function editRequestFromList(requestId) {
    // 先获取请求详情，然后显示编辑模态框
    apiRequest(`/requests/${requestId}`)
        .then(response => {
            const request = response.data;
            showEditRequestModalWithData(request);
        })
        .catch(error => {
            console.error('Failed to load request:', error);
            showAlert('获取请求详情失败: ' + error.message, 'danger');
        });
}

// 显示编辑交易请求模态框
function showEditRequestModal() {
    // 从详情模态框获取请求ID
    const requestId = document.getElementById('requestDetailContent').dataset.requestId;
    if (requestId) {
        editRequestFromList(requestId);
    }
}

// 使用数据显示编辑模态框
function showEditRequestModalWithData(request) {
    // 填充表单数据
    document.getElementById('editRequestId').value = request.request_id;
    document.getElementById('editRequestItem').value = request.item_title || '';
    document.getElementById('editRequestRequester').value = request.requester_username || '';
    document.getElementById('editRequestMessage').value = request.message || '';
    document.getElementById('editRequestStatus').value = request.status;
    document.getElementById('editRequestCreatedAt').value = formatDateTime(request.created_at);
    document.getElementById('editRequestUpdatedAt').value = formatDateTime(request.updated_at);
    
    // 显示模态框
    const modal = new bootstrap.Modal(document.getElementById('editRequestModal'));
    modal.show();
}

// 更新交易请求
async function updateRequest() {
    try {
        const requestId = document.getElementById('editRequestId').value;
        const message = document.getElementById('editRequestMessage').value.trim();
        const status = document.getElementById('editRequestStatus').value;
        
        const updateData = {
            message: message || null,
            status: status
        };
        
        await apiRequest(`/requests/${requestId}/admin`, {
            method: 'PUT',
            body: JSON.stringify(updateData)
        });
        
        showAlert('交易请求更新成功', 'success');
        
        // 关闭模态框
        const modal = bootstrap.Modal.getInstance(document.getElementById('editRequestModal'));
        modal.hide();
        
        // 刷新列表
        loadRequests();
        
    } catch (error) {
        console.error('Failed to update request:', error);
        showAlert('更新交易请求失败: ' + error.message, 'danger');
    }
}

// 更改交易请求状态
async function changeRequestStatus(requestId, newStatus) {
    try {
        const confirmed = confirm(`确定要将交易请求状态更改为"${getRequestStatusText(newStatus)}"吗？`);
        if (!confirmed) return;
        
        await apiRequest(`/requests/${requestId}/admin`, {
            method: 'PUT',
            body: JSON.stringify({ status: newStatus })
        });
        
        showAlert('状态更新成功', 'success');
        loadRequests();
        
    } catch (error) {
        console.error('Failed to change status:', error);
        showAlert('状态更新失败: ' + error.message, 'danger');
    }
}

// 删除交易请求
async function deleteRequest(requestId) {
    try {
        const confirmed = confirm('确定要删除这个交易请求吗？此操作不可撤销。');
        if (!confirmed) return;
        
        await apiRequest(`/requests/${requestId}`, {
            method: 'DELETE'
        });
        
        showAlert('交易请求删除成功', 'success');
        loadRequests();
        
    } catch (error) {
        console.error('Failed to delete request:', error);
        showAlert('删除交易请求失败: ' + error.message, 'danger');
    }
}

// 显示交易请求详情
function showRequestDetail(requestId) {
    apiRequest(`/requests/${requestId}`)
        .then(response => {
            const request = response.data;
            displayRequestDetail(request);
            
            // 保存请求ID到详情容器
            document.getElementById('requestDetailContent').dataset.requestId = request.request_id;
            
            // 显示模态框
            const modal = new bootstrap.Modal(document.getElementById('requestDetailModal'));
            modal.show();
        })
        .catch(error => {
            console.error('Failed to load request detail:', error);
            showAlert('获取请求详情失败: ' + error.message, 'danger');
        });
}

// 显示交易请求详情内容
function displayRequestDetail(request) {
    const content = document.getElementById('requestDetailContent');
    
    content.innerHTML = `
        <div class="row">
            <div class="col-md-6">
                <h6>基本信息</h6>
                <table class="table table-sm">
                    <tr><td><strong>请求ID:</strong></td><td>${request.request_id}</td></tr>
                    <tr><td><strong>状态:</strong></td><td><span class="status-badge status-${request.status}">${getRequestStatusText(request.status)}</span></td></tr>
                    <tr><td><strong>创建时间:</strong></td><td>${formatDateTime(request.created_at)}</td></tr>
                    <tr><td><strong>更新时间:</strong></td><td>${formatDateTime(request.updated_at)}</td></tr>
                </table>
            </div>
            <div class="col-md-6">
                <h6>参与者信息</h6>
                <table class="table table-sm">
                    <tr><td><strong>请求者:</strong></td><td>${request.requester_username || '-'}</td></tr>
                    <tr><td><strong>物品所有者:</strong></td><td>${request.item?.owner_username || '-'}</td></tr>
                </table>
            </div>
        </div>
        
        <div class="row mt-3">
            <div class="col-12">
                <h6>物品信息</h6>
                <div class="card">
                    <div class="card-body">
                        <h6 class="card-title">${request.item?.title || '未知物品'}</h6>
                        <p class="card-text">${request.item?.description || '无描述'}</p>
                        <small class="text-muted">分类: ${request.item?.category_name || '未分类'} | 状态: ${request.item?.status || '未知'}</small>
                    </div>
                </div>
            </div>
        </div>
        
        ${request.message ? `
        <div class="row mt-3">
            <div class="col-12">
                <h6>附言</h6>
                <div class="alert alert-info">
                    ${request.message}
                </div>
            </div>
        </div>
        ` : ''}
    `;
}

// 获取请求状态文本
function getRequestStatusText(status) {
    const statusMap = {
        'pending': '待处理',
        'accepted': '已接受',
        'rejected': '已拒绝',
        'cancelled': '已取消',
        'completed': '已完成'
    };
    return statusMap[status] || status;
}

// 处理下拉菜单显示时的容器overflow问题
document.addEventListener('DOMContentLoaded', function() {
    // 监听所有下拉菜单的显示/隐藏事件
    document.addEventListener('show.bs.dropdown', function(event) {
        const dropdownMenu = event.target.nextElementSibling;
        if (dropdownMenu && dropdownMenu.classList.contains('dropdown-menu')) {
            // 获取触发按钮的位置
            const rect = event.target.getBoundingClientRect();
            
            // 将下拉菜单移动到body下
            document.body.appendChild(dropdownMenu);
            
            // 设置绝对定位
            dropdownMenu.style.position = 'fixed';
            dropdownMenu.style.top = (rect.bottom + 2) + 'px';
            dropdownMenu.style.left = rect.left + 'px';
            dropdownMenu.style.zIndex = '99999';
            dropdownMenu.style.display = 'block';
            
            // 标记为已移动
            dropdownMenu.setAttribute('data-moved', 'true');
            dropdownMenu.setAttribute('data-original-parent', event.target.parentElement.className);
        }
        
        const tableResponsive = event.target.closest('.table-responsive');
        if (tableResponsive) {
            tableResponsive.classList.add('dropdown-menu-visible');
        }
    });
    
    document.addEventListener('hide.bs.dropdown', function(event) {
        const dropdownMenu = document.querySelector('.dropdown-menu[data-moved="true"]');
        if (dropdownMenu) {
            // 将下拉菜单移回原位置
            const btnGroup = event.target.parentElement;
            if (btnGroup) {
                btnGroup.appendChild(dropdownMenu);
            }
            
            // 重置样式
            dropdownMenu.style.position = '';
            dropdownMenu.style.top = '';
            dropdownMenu.style.left = '';
            dropdownMenu.style.zIndex = '';
            dropdownMenu.style.display = '';
            dropdownMenu.removeAttribute('data-moved');
            dropdownMenu.removeAttribute('data-original-parent');
        }
        
        const tableResponsive = event.target.closest('.table-responsive');
        if (tableResponsive) {
            tableResponsive.classList.remove('dropdown-menu-visible');
        }
    });
});
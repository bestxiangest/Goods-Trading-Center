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
            loadUsers();
            break;
        case 'items':
            loadItems();
            loadCategories(); // 为筛选器加载分类
            break;
        case 'categories':
            loadCategories();
            break;
        case 'requests':
            loadRequests();
            break;
        case 'reviews':
            loadReviews();
            break;
        case 'messages':
            loadMessages();
            break;
        case 'statistics':
            loadStatistics();
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
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .catch(error => {
            console.error('API request failed:', error);
            showAlert('请求失败: ' + error.message, 'danger');
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
        apiRequest('/statistics/today')
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
    apiRequest('/statistics/user-registration-trend')
        .then(response => {
            const data = response.data || [];
            const labels = data.map(item => item.date);
            const values = data.map(item => item.count);
            
            const ctx = document.getElementById('userChart').getContext('2d');
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
    apiRequest('/statistics/item-category-distribution')
        .then(response => {
            const data = response.data || [];
            const labels = data.map(item => item.category);
            const values = data.map(item => item.count);
            
            const ctx = document.getElementById('categoryChart').getContext('2d');
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
            displayUsers(data.items || []);
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
            <td>${user.id}</td>
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
                <span class="badge ${user.role === 'admin' ? 'bg-danger' : 'bg-primary'}">
                    ${user.role === 'admin' ? '管理员' : '普通用户'}
                </span>
            </td>
            <td>${formatDateTime(user.created_at)}</td>
            <td>
                <button class="btn btn-sm btn-outline-primary" onclick="showUserDetail(${user.id})">
                    <i class="fas fa-eye"></i>
                </button>
                ${user.role !== 'admin' ? `
                    <button class="btn btn-sm btn-outline-warning ms-1" onclick="toggleUserStatus(${user.id})">
                        <i class="fas fa-ban"></i>
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
            <td>${item.id}</td>
            <td>
                <div class="d-flex align-items-center">
                    ${item.images && item.images.length > 0 ? 
                        `<img src="${item.images[0]}" alt="${item.title}" class="me-2" style="width: 40px; height: 40px; object-fit: cover; border-radius: 4px;">` : 
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
                <button class="btn btn-sm btn-outline-primary" onclick="showItemDetail(${item.id})">
                    <i class="fas fa-eye"></i>
                </button>
                <button class="btn btn-sm btn-outline-danger ms-1" onclick="deleteItem(${item.id})">
                    <i class="fas fa-trash"></i>
                </button>
            </td>
        </tr>
    `).join('');
}

// 加载分类数据
function loadCategories() {
    apiRequest('/categories')
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
    
    // 构建分类树
    const tree = buildCategoryTree(categories);
    container.innerHTML = renderCategoryTree(tree);
}

// 构建分类树结构
function buildCategoryTree(categories) {
    const tree = [];
    const map = {};
    
    // 创建映射
    categories.forEach(category => {
        map[category.id] = { ...category, children: [] };
    });
    
    // 构建树结构
    categories.forEach(category => {
        if (category.parent_id) {
            if (map[category.parent_id]) {
                map[category.parent_id].children.push(map[category.id]);
            }
        } else {
            tree.push(map[category.id]);
        }
    });
    
    return tree;
}

// 渲染分类树
function renderCategoryTree(tree) {
    return tree.map(category => `
        <div class="category-item parent">
            <div class="d-flex justify-content-between align-items-center">
                <span>
                    <i class="fas fa-folder me-2"></i>
                    ${category.name}
                </span>
                <div>
                    <button class="btn btn-sm btn-outline-light" onclick="editCategory(${category.id})">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-light ms-1" onclick="deleteCategory(${category.id})">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
            ${category.children.length > 0 ? `
                <div class="mt-2">
                    ${category.children.map(child => `
                        <div class="category-item child">
                            <div class="d-flex justify-content-between align-items-center">
                                <span>
                                    <i class="fas fa-file me-2"></i>
                                    ${child.name}
                                </span>
                                <div>
                                    <button class="btn btn-sm btn-outline-primary" onclick="editCategory(${child.id})">
                                        <i class="fas fa-edit"></i>
                                    </button>
                                    <button class="btn btn-sm btn-outline-danger ms-1" onclick="deleteCategory(${child.id})">
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
    
    if (itemCategoryFilter) {
        const currentValue = itemCategoryFilter.value;
        itemCategoryFilter.innerHTML = '<option value="">全部分类</option>' +
            categories.map(cat => `<option value="${cat.id}">${cat.name}</option>`).join('');
        itemCategoryFilter.value = currentValue;
    }
    
    if (parentCategorySelect) {
        parentCategorySelect.innerHTML = '<option value="">无（顶级分类）</option>' +
            categories.filter(cat => !cat.parent_id)
                .map(cat => `<option value="${cat.id}">${cat.name}</option>`).join('');
    }
}

// 加载交易请求数据
function loadRequests(page = 1, statusFilter = '') {
    const params = new URLSearchParams({
        page: page,
        per_page: pageSize
    });
    
    if (statusFilter) params.append('status', statusFilter);
    
    apiRequest(`/requests?${params}`)
        .then(data => {
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
                <button class="btn btn-sm btn-outline-primary" onclick="showRequestDetail(${request.id})">
                    <i class="fas fa-eye"></i>
                </button>
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
            displayReviews(data.reviews || []);
            updatePagination('reviews', data.pagination || {});
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
        .then(data => {
            displayMessages(data.messages || []);
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
            <td>${message.id}</td>
            <td>${message.sender_username || '系统'}</td>
            <td>${message.receiver_username || '-'}</td>
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
                <button class="btn btn-sm btn-outline-danger" onclick="deleteMessage(${message.id})">
                    <i class="fas fa-trash"></i>
                </button>
            </td>
        </tr>
    `).join('');
}

// 加载统计数据
function loadStatistics() {
    // 加载各种统计图表
    loadTransactionStatusChart();
    loadMonthlyActivityChart();
    loadReputationChart();
}

// 加载交易状态分布图
function loadTransactionStatusChart() {
    apiRequest('/statistics/request-status-distribution')
        .then(data => {
            const ctx = document.getElementById('transactionStatusChart').getContext('2d');
            new Chart(ctx, {
                type: 'pie',
                data: {
                    labels: data.labels || [],
                    datasets: [{
                        data: data.values || [],
                        backgroundColor: [
                            '#4e73df',
                            '#1cc88a',
                            '#36b9cc',
                            '#f6c23e',
                            '#e74a3b'
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
            console.error('Failed to load transaction status chart:', error);
        });
}

// 加载月度活跃度图
function loadMonthlyActivityChart() {
    // 暂时使用用户注册趋势数据
    apiRequest('/statistics/user-registration-trend')
        .then(data => {
            const ctx = document.getElementById('monthlyActivityChart').getContext('2d');
            new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: data.labels || [],
                    datasets: [{
                        label: '新注册用户数',
                        data: data.values || [],
                        backgroundColor: '#4e73df',
                        borderColor: '#4e73df',
                        borderWidth: 1
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
            console.error('Failed to load monthly activity chart:', error);
        });
}

// 加载用户信誉分布图
function loadReputationChart() {
    // 暂时使用分类分布数据
    apiRequest('/statistics/item-category-distribution')
        .then(data => {
            const ctx = document.getElementById('reputationChart').getContext('2d');
            new Chart(ctx, {
                type: 'histogram',
                data: {
                    labels: data.labels || [],
                    datasets: [{
                        label: '用户数量',
                        data: data.values || [],
                        backgroundColor: '#1cc88a',
                        borderColor: '#1cc88a',
                        borderWidth: 1
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
            console.error('Failed to load reputation chart:', error);
        });
}

// 更新分页
function updatePagination(section, pagination) {
    const paginationContainer = document.getElementById(`${section}-pagination`);
    if (!paginationContainer || !pagination.pages) {
        return;
    }
    
    const currentPage = pagination.page || 1;
    const totalPages = pagination.pages;
    
    let paginationHTML = '';
    
    // 上一页
    if (currentPage > 1) {
        paginationHTML += `
            <li class="page-item">
                <a class="page-link" href="#" onclick="changePage('${section}', ${currentPage - 1})">
                    <i class="fas fa-chevron-left"></i>
                </a>
            </li>
        `;
    }
    
    // 页码
    const startPage = Math.max(1, currentPage - 2);
    const endPage = Math.min(totalPages, currentPage + 2);
    
    for (let i = startPage; i <= endPage; i++) {
        paginationHTML += `
            <li class="page-item ${i === currentPage ? 'active' : ''}">
                <a class="page-link" href="#" onclick="changePage('${section}', ${i})">${i}</a>
            </li>
        `;
    }
    
    // 下一页
    if (currentPage < totalPages) {
        paginationHTML += `
            <li class="page-item">
                <a class="page-link" href="#" onclick="changePage('${section}', ${currentPage + 1})">
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

function refreshStatistics() {
    loadStatistics();
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
            document.getElementById('userDetailContent').innerHTML = `
                <div class="row">
                    <div class="col-md-6">
                        <h6>基本信息</h6>
                        <p><strong>用户名:</strong> ${user.username}</p>
                        <p><strong>邮箱:</strong> ${user.email}</p>
                        <p><strong>手机号:</strong> ${user.phone || '-'}</p>
                        <p><strong>地址:</strong> ${user.address || '-'}</p>
                        <p><strong>角色:</strong> ${user.role === 'admin' ? '管理员' : '普通用户'}</p>
                    </div>
                    <div class="col-md-6">
                        <h6>统计信息</h6>
                        <p><strong>信誉评分:</strong> 
                            <div class="rating-stars">
                                ${generateStars(user.reputation_score || 0)}
                                <span class="ms-1">${(user.reputation_score || 0).toFixed(1)}</span>
                            </div>
                        </p>
                        <p><strong>发布物品数:</strong> ${user.items_count || 0}</p>
                        <p><strong>交易次数:</strong> ${user.transactions_count || 0}</p>
                        <p><strong>注册时间:</strong> ${formatDateTime(user.created_at)}</p>
                        <p><strong>最后登录:</strong> ${formatDateTime(user.last_login)}</p>
                    </div>
                </div>
            `;
            modal.show();
        })
        .catch(error => {
            console.error('Failed to load user detail:', error);
        });
}

function showItemDetail(itemId) {
    apiRequest(`/items/${itemId}`)
        .then(item => {
            const modal = new bootstrap.Modal(document.getElementById('itemDetailModal'));
            document.getElementById('itemDetailContent').innerHTML = `
                <div class="row">
                    <div class="col-md-6">
                        <h6>物品信息</h6>
                        <p><strong>标题:</strong> ${item.title}</p>
                        <p><strong>描述:</strong> ${item.description || '-'}</p>
                        <p><strong>分类:</strong> ${item.category_name || '-'}</p>
                        <p><strong>状态:</strong> 
                            <span class="status-badge status-${item.status}">
                                ${getStatusText(item.status)}
                            </span>
                        </p>
                        <p><strong>新旧程度:</strong> ${getConditionText(item.condition)}</p>
                        <p><strong>发布者:</strong> ${item.owner_username || '-'}</p>
                    </div>
                    <div class="col-md-6">
                        <h6>其他信息</h6>
                        <p><strong>发布时间:</strong> ${formatDateTime(item.created_at)}</p>
                        <p><strong>更新时间:</strong> ${formatDateTime(item.updated_at)}</p>
                        ${item.images && item.images.length > 0 ? `
                            <div>
                                <strong>图片:</strong>
                                <div class="mt-2">
                                    ${item.images.map(img => `
                                        <img src="${img}" alt="物品图片" class="me-2 mb-2" style="width: 80px; height: 80px; object-fit: cover; border-radius: 4px;">
                                    `).join('')}
                                </div>
                            </div>
                        ` : ''}
                    </div>
                </div>
            `;
            modal.show();
        })
        .catch(error => {
            console.error('Failed to load item detail:', error);
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

// 分类管理函数
function showAddCategoryModal() {
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
        });
    }
}
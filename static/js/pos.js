// C:/.../comphone_integrated/static/js/pos.js

document.addEventListener('DOMContentLoaded', function() {
    const productSearchInput = document.getElementById('product-search');
    const searchResultsDiv = document.getElementById('search-results');
    const cartItemsUl = document.getElementById('cart-items');
    const cartTotalSpan = document.getElementById('cart-total');
    const processSaleBtn = document.getElementById('process-sale-btn');
    const paymentMethodSelect = document.getElementById('payment-method');

    let cart = []; // Array to hold cart items: {id, name, price, quantity}

    // --- Search Functionality ---
    productSearchInput.addEventListener('input', debounce(async function() {
        const query = this.value.trim();
        if (query.length < 2) {
            searchResultsDiv.innerHTML = '';
            return;
        }

        try {
            const response = await fetch(`/pos/api/search-products?q=${query}`);
            const products = await response.json();
            displaySearchResults(products);
        } catch (error) {
            console.error('Error searching products:', error);
        }
    }, 300));

    function displaySearchResults(products) {
        searchResultsDiv.innerHTML = '';
        if (products.length === 0) {
            searchResultsDiv.innerHTML = '<div class="list-group-item">ไม่พบสินค้า</div>';
            return;
        }
        products.forEach(product => {
            const item = document.createElement('a');
            item.href = '#';
            item.className = 'list-group-item list-group-item-action';
            item.textContent = `${product.name} (คงเหลือ: ${product.quantity}) - ฿${product.price}`;
            item.dataset.productId = product.id;
            item.addEventListener('click', (e) => {
                e.preventDefault();
                addProductToCart(product);
                productSearchInput.value = '';
                searchResultsDiv.innerHTML = '';
            });
            searchResultsDiv.appendChild(item);
        });
    }

    // --- Cart Management ---
    function addProductToCart(product) {
        const existingItem = cart.find(item => item.id === product.id);
        if (existingItem) {
            existingItem.quantity++;
        } else {
            cart.push({
                id: product.id,
                name: product.name,
                price: product.price,
                quantity: 1
            });
        }
        renderCart();
    }

    function renderCart() {
        cartItemsUl.innerHTML = '';
        let total = 0;

        if (cart.length === 0) {
            cartItemsUl.innerHTML = '<li class="text-muted">ตะกร้าว่าง</li>';
        } else {
            cart.forEach((item, index) => {
                const li = document.createElement('li');
                li.innerHTML = `
                    <span>${item.name} (฿${item.price})</span>
                    <div>
                        <button class="btn btn-sm btn-secondary" data-index="${index}" onclick="updateQuantity(${index}, -1)">-</button>
                        <span class="mx-2">${item.quantity}</span>
                        <button class="btn btn-sm btn-secondary" data-index="${index}" onclick="updateQuantity(${index}, 1)">+</button>
                        <button class="btn btn-sm btn-danger ms-2" data-index="${index}" onclick="removeFromCart(${index})">
                            <i class="fas fa-trash-alt"></i>
                        </button>
                    </div>
                `;
                cartItemsUl.appendChild(li);
                total += item.price * item.quantity;
            });
        }
        cartTotalSpan.textContent = `฿${total.toFixed(2)}`;
    }

    // Make these functions globally accessible from the inline HTML
    window.updateQuantity = function(index, change) {
        const item = cart[index];
        if (item) {
            item.quantity += change;
            if (item.quantity <= 0) {
                cart.splice(index, 1); // Remove if quantity is 0 or less
            }
            renderCart();
        }
    };

    window.removeFromCart = function(index) {
        cart.splice(index, 1);
        renderCart();
    };

    // --- Process Sale ---
    processSaleBtn.addEventListener('click', async function() {
        if (cart.length === 0) {
            alert('กรุณาเพิ่มสินค้าลงในตะกร้าก่อน');
            return;
        }

        const saleData = {
            cart: cart,
            total: parseFloat(cartTotalSpan.textContent.replace('฿', '')),
            paymentMethod: paymentMethodSelect.value,
            customerId: null // Can be enhanced to add customer selection
        };
        
        this.disabled = true;
        this.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> กำลังบันทึก...';

        try {
            const response = await fetch('/pos/api/process-sale', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(saleData)
            });
            const result = await response.json();
            if (result.success) {
                alert(result.message);
                // Open receipt in a new tab
                window.open(`/pos/receipt/${result.sale_id}`, '_blank');
                // Reset POS
                cart = [];
                renderCart();
            } else {
                alert(`เกิดข้อผิดพลาด: ${result.message}`);
            }
        } catch (error) {
            console.error('Error processing sale:', error);
            alert('การเชื่อมต่อกับเซิร์ฟเวอร์ล้มเหลว');
        } finally {
            this.disabled = false;
            this.innerHTML = '<i class="fas fa-check-circle"></i> ยืนยันการขาย';
        }
    });

    // Debounce utility
    function debounce(func, delay) {
        let timeout;
        return function(...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), delay);
        };
    }

    // Initial render
    renderCart();
});
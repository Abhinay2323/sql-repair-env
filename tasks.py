"""
Task definitions for the SQL Repair Environment.

Each task has:
  - db_setup:       SQL to create and populate tables
  - broken_query:   The query the agent must fix
  - expected_query: The correct query (used to generate ground truth)
  - schema_info:    Human-readable schema description shown to the agent
  - task_description: Natural language description of what the query should return
  - max_steps:      Maximum allowed attempts
  - ordered:        Whether result ordering matters for scoring
"""

# ---------------------------------------------------------------------------
# TASK 1  ·  fix_syntax  ·  EASY
# Three typos: misspelled column (salry), table (emplyees), keyword (ORER BY)
# ---------------------------------------------------------------------------

TASK_FIX_SYNTAX_SETUP = """
CREATE TABLE employees (
    id         INTEGER PRIMARY KEY,
    name       TEXT    NOT NULL,
    department TEXT    NOT NULL,
    salary     REAL    NOT NULL,
    hire_date  TEXT    NOT NULL
);

INSERT INTO employees VALUES
(1, 'Alice Johnson', 'Engineering', 95000.0, '2021-03-15'),
(2, 'Bob Smith',     'Marketing',   72000.0, '2020-01-10'),
(3, 'Carol White',   'Engineering', 88000.0, '2019-07-22'),
(4, 'David Brown',   'HR',          65000.0, '2022-05-01'),
(5, 'Eve Davis',     'Engineering', 102000.0,'2018-11-30'),
(6, 'Frank Wilson',  'Marketing',   78000.0, '2021-09-14'),
(7, 'Grace Lee',     'HR',          69000.0, '2020-03-22');
"""

TASK_FIX_SYNTAX_BROKEN = """\
SELECT name, salry
FROM emplyees
WHERE departmnt = 'Engineering'
ORER BY salary DESC;\
"""

TASK_FIX_SYNTAX_EXPECTED = """\
SELECT name, salary
FROM employees
WHERE department = 'Engineering'
ORDER BY salary DESC;\
"""

TASK_FIX_SYNTAX_SCHEMA = """\
Table: employees
  id          INTEGER   PRIMARY KEY
  name        TEXT      Employee full name
  department  TEXT      Department name (e.g. 'Engineering', 'Marketing', 'HR')
  salary      REAL      Annual salary in USD
  hire_date   TEXT      ISO date string (YYYY-MM-DD)\
"""

TASK_FIX_SYNTAX_DESCRIPTION = """\
Return the name and salary of all employees in the 'Engineering' department,
sorted by salary from highest to lowest.

The query has THREE syntax errors (typos). Fix all of them.\
"""

# ---------------------------------------------------------------------------
# TASK 2  ·  fix_logic  ·  MEDIUM
# Wrong JOIN condition: orders joined on product_id instead of customer_id
# ---------------------------------------------------------------------------

TASK_FIX_LOGIC_SETUP = """
CREATE TABLE customers (
    customer_id   INTEGER PRIMARY KEY,
    customer_name TEXT    NOT NULL,
    email         TEXT    NOT NULL,
    city          TEXT    NOT NULL
);

CREATE TABLE products (
    product_id   INTEGER PRIMARY KEY,
    product_name TEXT    NOT NULL,
    price        REAL    NOT NULL,
    category     TEXT    NOT NULL
);

CREATE TABLE orders (
    order_id    INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    product_id  INTEGER NOT NULL,
    quantity    INTEGER NOT NULL,
    order_date  TEXT    NOT NULL
);

INSERT INTO customers VALUES
(1, 'Alpha Corp',   'alpha@corp.com',   'New York'),
(2, 'Beta LLC',     'beta@llc.com',     'Chicago'),
(3, 'Gamma Inc',    'gamma@inc.com',    'Los Angeles'),
(4, 'Delta Co',     'delta@co.com',     'Houston'),
(5, 'Epsilon Ltd',  'epsilon@ltd.com',  'Phoenix');

INSERT INTO products VALUES
(1, 'Laptop',    1200.0, 'Electronics'),
(2, 'Desk Chair', 350.0, 'Furniture'),
(3, 'Monitor',    450.0, 'Electronics'),
(4, 'Keyboard',   120.0, 'Electronics'),
(5, 'Notebook',    15.0, 'Stationery');

INSERT INTO orders VALUES
( 1, 1, 1, 2,  '2024-03-15'),
( 2, 1, 3, 1,  '2024-04-10'),
( 3, 2, 2, 4,  '2024-02-20'),
( 4, 2, 4, 3,  '2024-05-01'),
( 5, 3, 1, 1,  '2024-01-12'),
( 6, 3, 5, 10, '2024-06-18'),
( 7, 4, 3, 2,  '2024-03-25'),
( 8, 4, 1, 1,  '2024-04-02'),
( 9, 5, 2, 2,  '2024-02-14'),
(10, 1, 4, 5,  '2024-05-30');
"""

TASK_FIX_LOGIC_BROKEN = """\
SELECT c.customer_name, SUM(o.quantity) AS total_quantity
FROM customers c
JOIN orders o ON c.customer_id = o.product_id
WHERE o.order_date >= '2024-01-01'
GROUP BY c.customer_id, c.customer_name
ORDER BY total_quantity DESC
LIMIT 5;\
"""

TASK_FIX_LOGIC_EXPECTED = """\
SELECT c.customer_name, SUM(o.quantity) AS total_quantity
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
WHERE o.order_date >= '2024-01-01'
GROUP BY c.customer_id, c.customer_name
ORDER BY total_quantity DESC
LIMIT 5;\
"""

TASK_FIX_LOGIC_SCHEMA = """\
Table: customers
  customer_id    INTEGER  PRIMARY KEY
  customer_name  TEXT     Company/customer name
  email          TEXT     Contact email
  city           TEXT     Location city

Table: products
  product_id    INTEGER  PRIMARY KEY
  product_name  TEXT     Name of product
  price         REAL     Unit price in USD
  category      TEXT     Product category

Table: orders
  order_id    INTEGER  PRIMARY KEY
  customer_id INTEGER  FK → customers.customer_id
  product_id  INTEGER  FK → products.product_id
  quantity    INTEGER  Number of units ordered
  order_date  TEXT     ISO date string (YYYY-MM-DD)\
"""

TASK_FIX_LOGIC_DESCRIPTION = """\
Return the top 5 customers ranked by total units ordered in 2024,
showing customer_name and total_quantity.

The query contains a LOGICAL ERROR in the JOIN condition that causes
it to join on the wrong column, producing completely wrong results.
Find and fix it.\
"""

# ---------------------------------------------------------------------------
# TASK 3  ·  complex_analytics  ·  HARD
# Three bugs:
#   1. AVG instead of SUM for total_revenue
#   2. status filter uses 'COMPLETED' (uppercase) — SQLite is case-sensitive
#   3. HAVING filters on total_revenue > 100 instead of num_orders >= 2
# ---------------------------------------------------------------------------

TASK_COMPLEX_ANALYTICS_SETUP = """
CREATE TABLE users (
    user_id    INTEGER PRIMARY KEY,
    username   TEXT    NOT NULL,
    email      TEXT    NOT NULL,
    country    TEXT    NOT NULL,
    created_at TEXT    NOT NULL
);

CREATE TABLE orders (
    order_id   INTEGER PRIMARY KEY,
    user_id    INTEGER NOT NULL,
    status     TEXT    NOT NULL,
    created_at TEXT    NOT NULL
);

CREATE TABLE order_items (
    item_id    INTEGER PRIMARY KEY,
    order_id   INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity   INTEGER NOT NULL,
    unit_price REAL    NOT NULL
);

CREATE TABLE products (
    product_id   INTEGER PRIMARY KEY,
    product_name TEXT    NOT NULL,
    category     TEXT    NOT NULL
);

INSERT INTO users VALUES
(1, 'alice',   'alice@example.com',   'US', '2022-01-10'),
(2, 'bob',     'bob@example.com',     'UK', '2022-03-05'),
(3, 'charlie', 'charlie@example.com', 'US', '2022-06-20'),
(4, 'diana',   'diana@example.com',   'DE', '2021-11-15'),
(5, 'eve',     'eve@example.com',     'FR', '2023-02-28');

INSERT INTO products VALUES
(1, 'Laptop',     'Electronics'),
(2, 'Smartphone', 'Electronics'),
(3, 'Office Desk','Furniture'),
(4, 'Pen Pack',   'Stationery');

-- alice: 3 completed orders + 1 pending
INSERT INTO orders VALUES
( 1, 1, 'completed', '2024-02-10'),
( 2, 1, 'completed', '2024-03-15'),
( 3, 1, 'completed', '2024-05-01'),
( 4, 1, 'pending',   '2024-06-20');

-- bob: 2 completed orders
INSERT INTO orders VALUES
( 5, 2, 'completed', '2024-01-22'),
( 6, 2, 'completed', '2024-04-08');

-- charlie: 1 completed order (should be excluded by HAVING num_orders >= 2)
INSERT INTO orders VALUES
( 7, 3, 'completed', '2024-03-30');

-- diana: 3 completed orders
INSERT INTO orders VALUES
( 8, 4, 'completed', '2024-01-05'),
( 9, 4, 'completed', '2024-02-18'),
(10, 4, 'completed', '2024-05-25');

-- eve: 2 completed orders
INSERT INTO orders VALUES
(11, 5, 'completed', '2024-03-12'),
(12, 5, 'completed', '2024-04-30');

-- order_items  (order_id, product, qty, unit_price)
-- alice orders:  1→Laptop×1@1200, 2→Smartphone×2@800, 3→Desk×1@400, 4→pending(excluded)
INSERT INTO order_items VALUES
( 1, 1, 1, 1, 1200.0),
( 2, 2, 2, 2,  800.0),
( 3, 3, 3, 1,  400.0),
( 4, 4, 4, 2,   10.0);

-- bob orders: 5→Laptop×1@1200, 6→Smartphone×1@800
INSERT INTO order_items VALUES
( 5, 5, 1, 1, 1200.0),
( 6, 6, 2, 1,  800.0);

-- charlie order: 7→Pen Pack×5@2
INSERT INTO order_items VALUES
( 7, 7, 4, 5,    2.0);

-- diana orders: 8→Smartphone×2@800, 9→Desk×3@400, 10→Laptop×1@1200
INSERT INTO order_items VALUES
( 8, 8,  2, 2,  800.0),
( 9, 9,  3, 3,  400.0),
(10, 10, 1, 1, 1200.0);

-- eve orders: 11→Smartphone×1@800, 12→Desk×2@400
INSERT INTO order_items VALUES
(11, 11, 2, 1,  800.0),
(12, 12, 3, 2,  400.0);
"""

# Revenue per user (completed orders only, num_orders >= 2):
#   alice:  order 1→1200, order 2→1600, order 3→400  → total 3200, 3 orders
#   bob:    order 5→1200, order 6→800                → total 2000, 2 orders
#   diana:  order 8→1600, order 9→1200, order 10→1200 → total 4000, 3 orders
#   eve:    order 11→800, order 12→800                → total 1600, 2 orders
#   charlie excluded (1 order only)
# Sorted by total_revenue DESC: diana(4000), alice(3200), bob(2000), eve(1600)

TASK_COMPLEX_ANALYTICS_BROKEN = """\
WITH user_stats AS (
    SELECT
        u.user_id,
        u.username,
        COUNT(DISTINCT o.order_id)           AS num_orders,
        AVG(oi.quantity * oi.unit_price)     AS total_revenue
    FROM users u
    JOIN orders     o  ON u.user_id   = o.user_id
    JOIN order_items oi ON o.order_id = oi.order_id
    WHERE o.status = 'COMPLETED'
    GROUP BY u.user_id, u.username
    HAVING total_revenue > 100
)
SELECT username,
       num_orders,
       ROUND(total_revenue, 2) AS total_revenue
FROM user_stats
ORDER BY total_revenue DESC;\
"""

TASK_COMPLEX_ANALYTICS_EXPECTED = """\
WITH user_stats AS (
    SELECT
        u.user_id,
        u.username,
        COUNT(DISTINCT o.order_id)           AS num_orders,
        SUM(oi.quantity * oi.unit_price)     AS total_revenue
    FROM users u
    JOIN orders      o  ON u.user_id   = o.user_id
    JOIN order_items oi ON o.order_id  = oi.order_id
    WHERE o.status = 'completed'
    GROUP BY u.user_id, u.username
    HAVING num_orders >= 2
)
SELECT username,
       num_orders,
       ROUND(total_revenue, 2) AS total_revenue
FROM user_stats
ORDER BY total_revenue DESC;\
"""

TASK_COMPLEX_ANALYTICS_SCHEMA = """\
Table: users
  user_id    INTEGER  PRIMARY KEY
  username   TEXT     Login name
  email      TEXT     Email address
  country    TEXT     Two-letter country code
  created_at TEXT     ISO date string

Table: orders
  order_id   INTEGER  PRIMARY KEY
  user_id    INTEGER  FK → users.user_id
  status     TEXT     Order status: 'completed' | 'pending' | 'cancelled'
  created_at TEXT     ISO date string

Table: order_items
  item_id    INTEGER  PRIMARY KEY
  order_id   INTEGER  FK → orders.order_id
  product_id INTEGER  FK → products.product_id
  quantity   INTEGER  Units ordered
  unit_price REAL     Price per unit at time of order

Table: products
  product_id   INTEGER  PRIMARY KEY
  product_name TEXT     Product display name
  category     TEXT     Category label\
"""

TASK_COMPLEX_ANALYTICS_DESCRIPTION = """\
Find all users who have placed at least 2 completed orders.
For each qualifying user, return:
  - username
  - num_orders  (count of distinct completed orders)
  - total_revenue (sum of quantity × unit_price across all items in those orders, rounded to 2 decimals)

Sort results by total_revenue descending.

NOTE: 'pending' orders must be excluded. Only 'completed' orders count.

The query has THREE bugs — find and fix all of them.\
"""

# ---------------------------------------------------------------------------
# TASK 4  ·  fix_null_handling  ·  MEDIUM
# Bug: commission_rate can be NULL (meaning "use default 5%").
# The broken query multiplies sales_amount * commission_rate directly,
# producing NULL for reps with no rate — those rows silently contribute 0
# to SUM, giving wrong regional totals.
# Fix: wrap commission_rate with COALESCE(commission_rate, 0.05).
# ---------------------------------------------------------------------------

TASK_NULL_HANDLING_SETUP = """
CREATE TABLE sales_reps (
    rep_id          INTEGER PRIMARY KEY,
    rep_name        TEXT    NOT NULL,
    region          TEXT    NOT NULL,
    sales_amount    REAL    NOT NULL,
    commission_rate REAL            -- NULL means use default 5 %
);

INSERT INTO sales_reps VALUES
(1, 'Alice',  'North', 50000.0, 0.08),
(2, 'Bob',    'North', 30000.0, NULL),
(3, 'Carol',  'South', 45000.0, 0.07),
(4, 'David',  'South', 20000.0, NULL),
(5, 'Eve',    'East',  60000.0, 0.10),
(6, 'Frank',  'East',  25000.0, 0.06),
(7, 'Grace',  'West',  35000.0, NULL);
"""
# Expected totals:
#   East  = 60000*0.10 + 25000*0.06 = 6000 + 1500 = 7500
#   North = 50000*0.08 + 30000*0.05 = 4000 + 1500 = 5500
#   South = 45000*0.07 + 20000*0.05 = 3150 + 1000 = 4150
#   West  = 35000*0.05               =                1750

TASK_NULL_HANDLING_BROKEN = """\
SELECT region,
       ROUND(SUM(sales_amount * commission_rate), 2) AS total_commission
FROM sales_reps
GROUP BY region
ORDER BY total_commission DESC;\
"""

TASK_NULL_HANDLING_EXPECTED = """\
SELECT region,
       ROUND(SUM(sales_amount * COALESCE(commission_rate, 0.05)), 2) AS total_commission
FROM sales_reps
GROUP BY region
ORDER BY total_commission DESC;\
"""

TASK_NULL_HANDLING_SCHEMA = """\
Table: sales_reps
  rep_id          INTEGER  PRIMARY KEY
  rep_name        TEXT     Sales representative name
  region          TEXT     Sales region ('North', 'South', 'East', 'West')
  sales_amount    REAL     Total sales in USD for this rep
  commission_rate REAL     Commission rate (0.0 – 1.0); NULL = use company default of 0.05\
"""

TASK_NULL_HANDLING_DESCRIPTION = """\
Return the total commission earned per region, sorted from highest to lowest.

Commission for each rep = sales_amount × commission_rate.
Reps whose commission_rate is NULL should use the company default rate of 0.05.

The query has ONE bug that silently produces wrong totals for regions
that have reps with no commission_rate set. Find and fix it.\
"""

# ---------------------------------------------------------------------------
# TASK 5  ·  fix_duplicate_count  ·  MEDIUM
# Bug: COUNT(*) after a JOIN with order_items counts item rows, not orders.
# Classic fan-out trap: each order has multiple items, so joining inflates
# the count. Fix: COUNT(DISTINCT o.order_id).
# ---------------------------------------------------------------------------

TASK_DUPLICATE_COUNT_SETUP = """
CREATE TABLE customers (
    customer_id   INTEGER PRIMARY KEY,
    customer_name TEXT    NOT NULL
);

CREATE TABLE orders (
    order_id    INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    order_date  TEXT    NOT NULL
);

CREATE TABLE order_items (
    item_id   INTEGER PRIMARY KEY,
    order_id  INTEGER NOT NULL,
    product   TEXT    NOT NULL,
    quantity  INTEGER NOT NULL
);

INSERT INTO customers VALUES
(1, 'Alice'), (2, 'Bob'), (3, 'Carol'), (4, 'David');

-- Alice: 2 orders
INSERT INTO orders VALUES
(1, 1, '2024-01-10'),
(2, 1, '2024-02-15');

-- Bob: 1 order
INSERT INTO orders VALUES
(3, 2, '2024-01-20');

-- Carol: 2 orders
INSERT INTO orders VALUES
(4, 3, '2024-03-05'),
(5, 3, '2024-03-10');

-- David: 0 orders (excluded by INNER JOIN)

-- order_items: order 1 → 1 item, order 2 → 3 items
INSERT INTO order_items VALUES
(1, 1, 'Laptop',   1),
(2, 2, 'Mouse',    2),
(3, 2, 'Keyboard', 1),
(4, 2, 'Monitor',  1);

-- Bob order 3 → 2 items
INSERT INTO order_items VALUES
(5, 3, 'Desk',  1),
(6, 3, 'Chair', 2);

-- Carol order 4 → 1 item, order 5 → 2 items
INSERT INTO order_items VALUES
(7, 4, 'Notebook', 5),
(8, 5, 'Pen',     10),
(9, 5, 'Paper',    3);
"""
# Correct order_count: Alice=2, Carol=2, Bob=1
# Broken COUNT(*) would give: Alice=4(1+3), Carol=3(1+2), Bob=2

TASK_DUPLICATE_COUNT_BROKEN = """\
SELECT c.customer_name,
       COUNT(*) AS order_count
FROM customers c
JOIN orders     o  ON c.customer_id = o.customer_id
JOIN order_items oi ON o.order_id  = oi.order_id
GROUP BY c.customer_id, c.customer_name
ORDER BY order_count DESC, c.customer_name ASC;\
"""

TASK_DUPLICATE_COUNT_EXPECTED = """\
SELECT c.customer_name,
       COUNT(DISTINCT o.order_id) AS order_count
FROM customers c
JOIN orders     o  ON c.customer_id = o.customer_id
JOIN order_items oi ON o.order_id  = oi.order_id
GROUP BY c.customer_id, c.customer_name
ORDER BY order_count DESC, c.customer_name ASC;\
"""

TASK_DUPLICATE_COUNT_SCHEMA = """\
Table: customers
  customer_id   INTEGER  PRIMARY KEY
  customer_name TEXT     Customer full name

Table: orders
  order_id    INTEGER  PRIMARY KEY
  customer_id INTEGER  FK → customers.customer_id
  order_date  TEXT     ISO date string (YYYY-MM-DD)

Table: order_items
  item_id   INTEGER  PRIMARY KEY
  order_id  INTEGER  FK → orders.order_id
  product   TEXT     Product name
  quantity  INTEGER  Units ordered\
"""

TASK_DUPLICATE_COUNT_DESCRIPTION = """\
Return each customer and the number of orders they have placed,
sorted by order_count descending (break ties alphabetically by customer_name).

Only include customers who have placed at least one order.

The query produces inflated order counts due to a subtle JOIN behaviour.
Find the ONE bug and fix it.\
"""

# ---------------------------------------------------------------------------
# TASK 6  ·  fix_window_rank  ·  HARD
# Bug: ROW_NUMBER() uses no PARTITION BY, so it ranks employees globally
# instead of per-department.  Result: only the 2 top-paid employees across
# the whole company are returned, not the top 2 per department.
# Fix: add PARTITION BY department inside the OVER clause.
# ---------------------------------------------------------------------------

TASK_WINDOW_RANK_SETUP = """
CREATE TABLE employees (
    emp_id     INTEGER PRIMARY KEY,
    emp_name   TEXT    NOT NULL,
    department TEXT    NOT NULL,
    salary     REAL    NOT NULL
);

INSERT INTO employees VALUES
(1, 'Alice',  'Engineering', 95000),
(2, 'Bob',    'Engineering', 88000),
(3, 'Carol',  'Engineering', 102000),
(4, 'David',  'Marketing',   72000),
(5, 'Eve',    'Marketing',   78000),
(6, 'Frank',  'Marketing',   68000),
(7, 'Grace',  'HR',          69000),
(8, 'Henry',  'HR',          65000),
(9, 'Iris',   'HR',          74000);
"""
# Expected (top 2 per dept, ordered dept ASC then salary DESC):
#   Engineering: Carol 102000, Alice 95000
#   HR:          Iris  74000,  Grace 69000
#   Marketing:   Eve   78000,  David 72000

TASK_WINDOW_RANK_BROKEN = """\
SELECT emp_name, department, salary, dept_rank
FROM (
    SELECT
        emp_name,
        department,
        salary,
        ROW_NUMBER() OVER (ORDER BY salary DESC) AS dept_rank
    FROM employees
)
WHERE dept_rank <= 2
ORDER BY department ASC, salary DESC;\
"""

TASK_WINDOW_RANK_EXPECTED = """\
SELECT emp_name, department, salary, dept_rank
FROM (
    SELECT
        emp_name,
        department,
        salary,
        ROW_NUMBER() OVER (PARTITION BY department ORDER BY salary DESC) AS dept_rank
    FROM employees
)
WHERE dept_rank <= 2
ORDER BY department ASC, salary DESC;\
"""

TASK_WINDOW_RANK_SCHEMA = """\
Table: employees
  emp_id     INTEGER  PRIMARY KEY
  emp_name   TEXT     Employee full name
  department TEXT     Department ('Engineering', 'Marketing', 'HR')
  salary     REAL     Annual salary in USD\
"""

TASK_WINDOW_RANK_DESCRIPTION = """\
Return the top 2 highest-paid employees in EACH department.
For every qualifying employee, return: emp_name, department, salary, dept_rank.

Sort the final result by department ascending, then salary descending within each department.

The query executes without error but returns wrong employees.
There is ONE bug in the window function definition. Find and fix it.\
"""

# ---------------------------------------------------------------------------
# Master task registry
# ---------------------------------------------------------------------------

TASKS: dict = {
    "fix_syntax": {
        "name": "fix_syntax",
        "difficulty": "easy",
        "max_steps": 8,
        "db_setup": TASK_FIX_SYNTAX_SETUP,
        "broken_query": TASK_FIX_SYNTAX_BROKEN,
        "expected_query": TASK_FIX_SYNTAX_EXPECTED,
        "schema_info": TASK_FIX_SYNTAX_SCHEMA,
        "task_description": TASK_FIX_SYNTAX_DESCRIPTION,
        "ordered": True,
    },
    "fix_logic": {
        "name": "fix_logic",
        "difficulty": "medium",
        "max_steps": 12,
        "db_setup": TASK_FIX_LOGIC_SETUP,
        "broken_query": TASK_FIX_LOGIC_BROKEN,
        "expected_query": TASK_FIX_LOGIC_EXPECTED,
        "schema_info": TASK_FIX_LOGIC_SCHEMA,
        "task_description": TASK_FIX_LOGIC_DESCRIPTION,
        "ordered": True,
    },
    "complex_analytics": {
        "name": "complex_analytics",
        "difficulty": "hard",
        "max_steps": 15,
        "db_setup": TASK_COMPLEX_ANALYTICS_SETUP,
        "broken_query": TASK_COMPLEX_ANALYTICS_BROKEN,
        "expected_query": TASK_COMPLEX_ANALYTICS_EXPECTED,
        "schema_info": TASK_COMPLEX_ANALYTICS_SCHEMA,
        "task_description": TASK_COMPLEX_ANALYTICS_DESCRIPTION,
        "ordered": True,
    },
    "fix_null_handling": {
        "name": "fix_null_handling",
        "difficulty": "medium",
        "max_steps": 10,
        "db_setup": TASK_NULL_HANDLING_SETUP,
        "broken_query": TASK_NULL_HANDLING_BROKEN,
        "expected_query": TASK_NULL_HANDLING_EXPECTED,
        "schema_info": TASK_NULL_HANDLING_SCHEMA,
        "task_description": TASK_NULL_HANDLING_DESCRIPTION,
        "ordered": True,
    },
    "fix_duplicate_count": {
        "name": "fix_duplicate_count",
        "difficulty": "medium",
        "max_steps": 10,
        "db_setup": TASK_DUPLICATE_COUNT_SETUP,
        "broken_query": TASK_DUPLICATE_COUNT_BROKEN,
        "expected_query": TASK_DUPLICATE_COUNT_EXPECTED,
        "schema_info": TASK_DUPLICATE_COUNT_SCHEMA,
        "task_description": TASK_DUPLICATE_COUNT_DESCRIPTION,
        "ordered": True,
    },
    "fix_window_rank": {
        "name": "fix_window_rank",
        "difficulty": "hard",
        "max_steps": 15,
        "db_setup": TASK_WINDOW_RANK_SETUP,
        "broken_query": TASK_WINDOW_RANK_BROKEN,
        "expected_query": TASK_WINDOW_RANK_EXPECTED,
        "schema_info": TASK_WINDOW_RANK_SCHEMA,
        "task_description": TASK_WINDOW_RANK_DESCRIPTION,
        "ordered": True,
    },
}

TASK_NAMES = list(TASKS.keys())

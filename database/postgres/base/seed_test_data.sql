-- Test data seed file for wadeulwadeul-heroes
-- This file populates the database with test data for development and testing
-- Run this AFTER init.sql

-- Clear existing test data (optional, uncomment if needed)
-- TRUNCATE app.enrollments CASCADE;
-- TRUNCATE app.classes CASCADE;
-- TRUNCATE app.users CASCADE;

-- ============================================
-- Users (OLD type - 클래스 생성자)
-- ============================================
INSERT INTO app.users (id, name, email, type, created_at, updated_at) VALUES
    ('550e8400-e29b-41d4-a716-446655440001', 'Kim Seon-saeng', 'teacher.kim@example.com', 'old', NOW(), NOW()),
    ('550e8400-e29b-41d4-a716-446655440002', 'Park Myung-in', 'master.park@example.com', 'old', NOW(), NOW()),
    ('550e8400-e29b-41d4-a716-446655440003', 'Lee Jang-in', NULL, 'old', NOW(), NOW())  -- email 없는 경우
ON CONFLICT (id) DO NOTHING;

-- ============================================
-- Users (YOUNG type - 클래스 신청자)
-- ============================================
INSERT INTO app.users (id, name, email, type, created_at, updated_at) VALUES
    ('550e8400-e29b-41d4-a716-446655440011', 'Choi Young-hee', 'young.choi@example.com', 'young', NOW(), NOW()),
    ('550e8400-e29b-41d4-a716-446655440012', 'Jung Min-ji', 'minji.jung@example.com', 'young', NOW(), NOW()),
    ('550e8400-e29b-41d4-a716-446655440013', 'Kang Ho-dong', 'hodong.kang@example.com', 'young', NOW(), NOW()),
    ('550e8400-e29b-41d4-a716-446655440014', 'Song Ji-hyo', NULL, 'young', NOW(), NOW()),  -- email 없는 경우
    ('550e8400-e29b-41d4-a716-446655440015', 'Lee Kwang-soo', 'kwangsoo@example.com', 'young', NOW(), NOW())
ON CONFLICT (id) DO NOTHING;

-- ============================================
-- Classes (OLD 사용자들이 생성한 클래스)
-- ============================================

-- Kim Seon-saeng의 클래스들
INSERT INTO app.classes (
    id,
    creator_id,
    category,
    location,
    duration_minutes,
    capacity,
    years_of_experience,
    job_description,
    materials,
    price_per_person,
    template,
    created_at,
    updated_at
) VALUES
    (
        '650e8400-e29b-41d4-a716-446655440001',
        '550e8400-e29b-41d4-a716-446655440001',
        'cooking',
        'Seoul Gangnam',
        120,
        10,
        '15y',
        'Korean cuisine instructor',
        'Rice, vegetables, seasoning',
        '50000',
        '한식 요리 기초 - 재료 제공',
        NOW(),
        NOW()
    ),
    (
        '650e8400-e29b-41d4-a716-446655440002',
        '550e8400-e29b-41d4-a716-446655440001',
        'baking',
        'Seoul Hongdae',
        180,
        8,
        '12y',
        'Baker',
        'Flour, butter, sugar',
        '65000',
        '빵 만들기 - 앞치마 지참',
        NOW(),
        NOW()
    ),
    (
        '650e8400-e29b-41d4-a716-446655440003',
        '550e8400-e29b-41d4-a716-446655440001',
        'kimchi',
        'Seoul Jongno',
        150,
        15,
        '20y',
        'Fermentation specialist',
        'Cabbage, chili flakes, salt',
        '40000',
        '김치 담그기 - 용기 제공',
        NOW(),
        NOW()
    )
ON CONFLICT (id) DO NOTHING;

-- Park Myung-in의 클래스들
INSERT INTO app.classes (
    id,
    creator_id,
    category,
    location,
    duration_minutes,
    capacity,
    years_of_experience,
    job_description,
    materials,
    price_per_person,
    template,
    created_at,
    updated_at
) VALUES
    (
        '650e8400-e29b-41d4-a716-446655440011',
        '550e8400-e29b-41d4-a716-446655440002',
        'pottery',
        'Busan Haeundae',
        180,
        6,
        '18y',
        'Ceramic artist',
        'Clay, wheel, glaze',
        '70000',
        '도자기 만들기 - 초보 환영',
        NOW(),
        NOW()
    ),
    (
        '650e8400-e29b-41d4-a716-446655440012',
        '550e8400-e29b-41d4-a716-446655440002',
        'painting',
        'Busan Seomyeon',
        120,
        12,
        '10y',
        'Watercolorist',
        'Paper, brushes, palette',
        '45000',
        '수채화 기초 - 재료 제공',
        NOW(),
        NOW()
    ),
    (
        '650e8400-e29b-41d4-a716-446655440013',
        '550e8400-e29b-41d4-a716-446655440002',
        'calligraphy',
        'Busan Gwangalli',
        90,
        10,
        '22y',
        'Calligrapher',
        'Brush, ink, paper',
        '35000',
        '서예 입문 - 붓 지참',
        NOW(),
        NOW()
    )
ON CONFLICT (id) DO NOTHING;

-- Lee Jang-in의 클래스들
INSERT INTO app.classes (
    id,
    creator_id,
    category,
    location,
    duration_minutes,
    capacity,
    years_of_experience,
    job_description,
    materials,
    price_per_person,
    template,
    created_at,
    updated_at
) VALUES
    (
        '650e8400-e29b-41d4-a716-446655440021',
        '550e8400-e29b-41d4-a716-446655440003',
        'gardening',
        'Incheon Songdo',
        120,
        15,
        '17y',
        'Urban gardener',
        'Seeds, soil, gloves',
        '30000',
        '텃밭 가꾸기 - 장갑 지참',
        NOW(),
        NOW()
    ),
    (
        '650e8400-e29b-41d4-a716-446655440022',
        '550e8400-e29b-41d4-a716-446655440003',
        'woodworking',
        'Incheon Bupyeong',
        180,
        8,
        '25y',
        'Woodcraft expert',
        'Wood, glue, safety gear',
        '80000',
        '목공예 기초 - 안전장비 제공',
        NOW(),
        NOW()
    )
ON CONFLICT (id) DO NOTHING;

-- ============================================
-- Enrollments (YOUNG 사용자들의 클래스 신청)
-- ============================================

-- cooking 클래스 신청자들 (Kim Seon-saeng)
INSERT INTO app.enrollments (id, class_id, user_id, applied_date, headcount) VALUES
    ('750e8400-e29b-41d4-a716-446655440001', '650e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440011', '2025-12-05', 2),
    ('750e8400-e29b-41d4-a716-446655440002', '650e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440012', '2025-12-06', 1),
    ('750e8400-e29b-41d4-a716-446655440003', '650e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440013', '2025-12-07', 3)
ON CONFLICT (id) DO NOTHING;

-- baking 클래스 신청자들 (Kim Seon-saeng)
INSERT INTO app.enrollments (id, class_id, user_id, applied_date, headcount) VALUES
    ('750e8400-e29b-41d4-a716-446655440011', '650e8400-e29b-41d4-a716-446655440002', '550e8400-e29b-41d4-a716-446655440014', '2025-12-08', 1),
    ('750e8400-e29b-41d4-a716-446655440012', '650e8400-e29b-41d4-a716-446655440002', '550e8400-e29b-41d4-a716-446655440015', '2025-12-09', 2)
ON CONFLICT (id) DO NOTHING;

-- kimchi 클래스 신청자 (Kim Seon-saeng) - 신청 없음 (테스트용)

-- pottery 클래스 신청자들 (Park Myung-in)
INSERT INTO app.enrollments (id, class_id, user_id, applied_date, headcount) VALUES
    ('750e8400-e29b-41d4-a716-446655440021', '650e8400-e29b-41d4-a716-446655440011', '550e8400-e29b-41d4-a716-446655440011', '2025-12-10', 1),
    ('750e8400-e29b-41d4-a716-446655440022', '650e8400-e29b-41d4-a716-446655440011', '550e8400-e29b-41d4-a716-446655440013', '2025-12-10', 2),
    ('750e8400-e29b-41d4-a716-446655440023', '650e8400-e29b-41d4-a716-446655440011', '550e8400-e29b-41d4-a716-446655440015', '2025-12-11', 1)
ON CONFLICT (id) DO NOTHING;

-- painting 클래스 신청자들 (Park Myung-in)
INSERT INTO app.enrollments (id, class_id, user_id, applied_date, headcount) VALUES
    ('750e8400-e29b-41d4-a716-446655440031', '650e8400-e29b-41d4-a716-446655440012', '550e8400-e29b-41d4-a716-446655440012', '2025-12-12', 2),
    ('750e8400-e29b-41d4-a716-446655440032', '650e8400-e29b-41d4-a716-446655440012', '550e8400-e29b-41d4-a716-446655440014', '2025-12-13', 1)
ON CONFLICT (id) DO NOTHING;

-- gardening 클래스 신청자들 (Lee Jang-in)
INSERT INTO app.enrollments (id, class_id, user_id, applied_date, headcount) VALUES
    ('750e8400-e29b-41d4-a716-446655440041', '650e8400-e29b-41d4-a716-446655440021', '550e8400-e29b-41d4-a716-446655440011', '2025-12-08', 1),
    ('750e8400-e29b-41d4-a716-446655440042', '650e8400-e29b-41d4-a716-446655440021', '550e8400-e29b-41d4-a716-446655440012', '2025-12-09', 1),
    ('750e8400-e29b-41d4-a716-446655440043', '650e8400-e29b-41d4-a716-446655440021', '550e8400-e29b-41d4-a716-446655440013', '2025-12-09', 2),
    ('750e8400-e29b-41d4-a716-446655440044', '650e8400-e29b-41d4-a716-446655440021', '550e8400-e29b-41d4-a716-446655440015', '2025-12-10', 1)
ON CONFLICT (id) DO NOTHING;

-- ============================================
-- 데이터 통계 출력 (검증용)
-- ============================================

-- 총 사용자 수
SELECT
    'Users Summary' as info,
    type,
    COUNT(*) as count,
    COUNT(email) as with_email,
    COUNT(*) - COUNT(email) as without_email
FROM app.users
GROUP BY type
ORDER BY type;

-- 총 클래스 수 (생성자별)
SELECT
    'Classes Summary' as info,
    u.name as creator_name,
    COUNT(c.id) as total_classes,
    COUNT(e.id) as total_enrollments
FROM app.classes c
JOIN app.users u ON c.creator_id = u.id
LEFT JOIN app.enrollments e ON c.id = e.class_id
GROUP BY u.name
ORDER BY u.name;

-- 클래스별 신청자 수
SELECT
    'Enrollment Summary' as info,
    c.category,
    c.location,
    COUNT(e.id) as enrollment_count,
    COALESCE(SUM(e.headcount), 0) as total_headcount,
    c.capacity
FROM app.classes c
LEFT JOIN app.enrollments e ON c.id = e.class_id
GROUP BY c.id, c.category, c.location, c.capacity
ORDER BY c.category;

-- ============================================
-- 참고: 데이터 초기화 쿼리 (필요시 사용)
-- ============================================
-- TRUNCATE app.enrollments CASCADE;
-- TRUNCATE app.classes CASCADE;
-- TRUNCATE app.users CASCADE;
-- TRUNCATE app.heroes CASCADE;

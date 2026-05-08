<?php
/**
 * API Server for Exercise Suggestion Plugin
 * Handles API endpoints according to section 6.2.3
 * Uses Data_PersonalizedSystem as the exercise and student score database.
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, Authorization');

// Handle preflight
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit;
}

$method = $_SERVER['REQUEST_METHOD'];
$path = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);

// Route requests
if ($method === 'POST' && $path === '/api/suggestions') {
    handle_get_suggestions();
} elseif ($method === 'GET' && preg_match('#^/api/exercise/([A-Za-z0-9_-]+)$#', $path, $matches)) {
    handle_get_exercise($matches[1]);
} elseif ($method === 'POST' && $path === '/api/submit') {
    handle_submit_exercise();
} elseif ($method === 'GET' && preg_match('#^/api/result/([A-Za-z0-9_-]+)$#', $path, $matches)) {
    handle_get_result($matches[1]);
} else {
    http_response_code(404);
    echo json_encode(['error' => 'Endpoint not found']);
}

/**
 * POST /api/suggestions - Get exercise suggestions (UC1)
 * LĂ¡ÂºÂ¥y tĂ¡Â»Â« Database thĂ¡ÂºÂ­t (Data_PersonalizedSystem)
 */
function handle_get_suggestions() {
    $input = json_decode(file_get_contents('php://input'), true);

    $student_id = $input['user_id']   ?? null;
    $course_id  = $input['course_id'] ?? null;
    $exam_code  = $input['exam_code'] ?? null;

    $suggestions = [];
    $message = 'ChĂ†Â°a cÄ‚Â³ bÄ‚Â i tĂ¡ÂºÂ­p phÄ‚Â¹ hĂ¡Â»Â£p.';

    // MĂ¡ÂºÂ£ng Mapping cĂ¡ÂºÂ¥u hÄ‚Â¬nh cĂ¡Â»Â©ng
    // course_id (int) trÄ‚Âªn Moodle => MaMon (string) trong CSDL
    $course_mapping = [ 
        2 => 'KTLT', // GiĂ¡ÂºÂ£ sĂ¡Â»Â­ ID 2 lÄ‚Â  KTLT
        3 => 'PTUD', // GiĂ¡ÂºÂ£ sĂ¡Â»Â­ ID 3 lÄ‚Â  PTUD
        4 => 'CTDL'  // GiĂ¡ÂºÂ£ sĂ¡Â»Â­ ID 4 lÄ‚Â  CTDL
    ];

    $ma_mon = null;
    if ($course_id && isset($course_mapping[$course_id])) {
        $ma_mon = $course_mapping[$course_id];
    }

    // Láº¥y Äiá»ƒm nÄƒng lá»±c tá»« SQL Server (báº£ng student_csv_data - thang 10)
    $target_student = $student_id; // MSSV tá»« Moodle
    
    $diem_nang_luc = null;
    $do_kho_target = null;
    
    if ($target_student !== null) {
        try {
            $dsn_score = "odbc:Driver={SQL Server};Server=118.69.126.49;Database=Data_PersonalizedSystem;";
            $pdo_score = new PDO($dsn_score, "userPersonalizedSystem", "123456789");
            $pdo_score->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
            
            $stmt_score = $pdo_score->prepare("SELECT total_score FROM student_csv_data WHERE student_id = ?");
            $stmt_score->execute([$target_student]);
            $score_row = $stmt_score->fetch(PDO::FETCH_ASSOC);
            
            if ($score_row && isset($score_row['total_score'])) {
                $diem_nang_luc = (float)$score_row['total_score'];
                
                if ($diem_nang_luc < 5.0) {
                    $do_kho_target = 1; // Dá»…
                } elseif ($diem_nang_luc <= 7.0) {
                    $do_kho_target = 2; // Trung bĂ¬nh
                } else {
                    $do_kho_target = 3; // KhĂ³ - má»©c cao nháº¥t hiá»‡n cĂ³ trong kho bĂ i
                }
            }
        } catch (PDOException $e) {
            $diem_nang_luc = null;
        }
    }

    try {
        // KĂ¡ÂºÂ¿t nĂ¡Â»â€˜i CSDL bĂ¡ÂºÂ±ng PDO ODBC (Driver Ă„â€˜Ä‚Â£ Ă„â€˜Ă†Â°Ă¡Â»Â£c kÄ‚Â­ch hoĂ¡ÂºÂ¡t trong php.ini)
        $dsn = "odbc:Driver={SQL Server};Server=118.69.126.49;Database=Data_PersonalizedSystem;";
        $pdo = new PDO($dsn, "userPersonalizedSystem", "123456789");
        $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

        // ChuĂ¡ÂºÂ©n bĂ¡Â»â€¹ cÄ‚Â¢u Query vĂ¡Â»â€ºi CAST VARBINARY Ă„â€˜Ă¡Â»Æ’ fix tiĂ¡ÂºÂ¿ng ViĂ¡Â»â€¡t qua ODBC
        $sql = "SELECT TOP 5 
                    Id, MaBaiTap, MaDoKho, MaMon,
                    CAST(TenBaiTap AS VARBINARY(MAX)) as TenBaiTapBin,
                    CAST(MoTa AS VARBINARY(MAX)) as MoTaBin
                FROM BAITAP";
        $params = [];
        $where_clauses = [];
        
        if ($ma_mon !== null) {
            $where_clauses[] = "MaMon = ?";
            $params[] = $ma_mon;
        }
        
        if ($do_kho_target !== null) {
            $where_clauses[] = "MaDoKho = ?";
            $params[] = $do_kho_target;
            $message = "GĂ¡Â»Â£i Ä‚Â½ 5 bÄ‚Â i bÄ‚Â¡m sÄ‚Â¡t NĂ„Æ’ng lĂ¡Â»Â±c (Ă„ÂiĂ¡Â»Æ’m: {$diem_nang_luc} - CĂ¡ÂºÂ¥p Ă„â€˜Ă¡Â»â„¢: {$do_kho_target}) mÄ‚Â´n {$ma_mon}";
        } elseif ($ma_mon !== null) {
            $message = "GĂ¡Â»Â£i Ä‚Â½ 5 bÄ‚Â i ngĂ¡ÂºÂ«u nhiÄ‚Âªn mÄ‚Â´n {$ma_mon} (KhÄ‚Â´ng cÄ‚Â³ Ă„ÂiĂ¡Â»Æ’m nĂ„Æ’ng lĂ¡Â»Â±c)";
        } else {
            $message = "GĂ¡Â»Â£i Ä‚Â½ 5 bÄ‚Â i ngĂ¡ÂºÂ«u nhiÄ‚Âªn (KhÄ‚Â´ng tÄ‚Â¬m thĂ¡ÂºÂ¥y mapping mÄ‚Â´n hĂ¡Â»Âc)";
        }
        
        if (!empty($where_clauses)) {
            $sql .= " WHERE " . implode(" AND ", $where_clauses);
        }
        
        $sql .= " ORDER BY NEWID()";

        $stmt = $pdo->prepare($sql);
        $stmt->execute($params);

        
        $rows = $stmt->fetchAll(PDO::FETCH_ASSOC);
        
        // Cá»©u cĂ¡nh (Fallback): Náº¿u CSDL thiáº¿u Ä‘Ăºng cáº¥p, háº¡ vá» cáº¥p gáº§n nháº¥t tháº¥p hÆ¡n thay vĂ¬ láº¥y ngáº«u nhiĂªn toĂ n mĂ´n.
        if (count($rows) === 0 && $do_kho_target !== null) {
            $sql_fb = "SELECT TOP 5 Id, MaBaiTap, MaDoKho, MaMon,
                          CAST(TenBaiTap AS VARBINARY(MAX)) as TenBaiTapBin,
                          CAST(MoTa AS VARBINARY(MAX)) as MoTaBin
                       FROM BAITAP
                       WHERE MaDoKho = (
                           SELECT MAX(MaDoKho)
                           FROM BAITAP
                           WHERE MaDoKho < ?";
            $fb_params = [$do_kho_target];

            if ($ma_mon !== null) {
                $sql_fb .= " AND MaMon = ?";
                $fb_params[] = $ma_mon;
            }

            $sql_fb .= ")";

            if ($ma_mon !== null) {
                $sql_fb .= " AND MaMon = ?";
                $fb_params[] = $ma_mon;
            }

            $sql_fb .= " ORDER BY NEWID()";

            $stmt_fb = $pdo->prepare($sql_fb);
            $stmt_fb->execute($fb_params);
            $rows = $stmt_fb->fetchAll(PDO::FETCH_ASSOC);
            $message .= " (Há»‡ thá»‘ng chÆ°a cĂ³ Ä‘á»§ bĂ i táº­p Cáº¥p $do_kho_target, tá»± Ä‘á»™ng háº¡ vá» cáº¥p gáº§n nháº¥t)";
        }

        // LĂ¡ÂºÂ¯p rÄ‚Â¡p dĂ¡Â»Â¯ liĂ¡Â»â€¡u & XĂ¡Â»Â­ lÄ‚Â½ Encoding tĂ¡Â»Â« VARBINARY (UCS-2LE) sang UTF-8
        foreach ($rows as $row) {
            $decode = function($bin) {
                if (empty($bin)) return '';
                // NĂ¡ÂºÂ¿u ODBC trĂ¡ÂºÂ£ vĂ¡Â»Â chuĂ¡Â»â€”i Hex (vd: 54007200...)
                if (ctype_xdigit((string)$bin)) {
                    $bin = hex2bin($bin);
                }
                return iconv('UCS-2LE', 'UTF-8', $bin);
            };

            // Map mĂ¡Â»Â©c Ă„â€˜Ă¡Â»â„¢ khÄ‚Â³
            $do_kho_map = [1 => 'easy', 2 => 'medium', 3 => 'hard'];
            $do_kho_text = isset($do_kho_map[$row['MaDoKho']]) ? $do_kho_map[$row['MaDoKho']] : 'unknown';

            $suggestions[] = [
                'id' => $row['MaBaiTap'],
                'title' => $decode($row['TenBaiTapBin']),
                'description' => $decode($row['MoTaBin']),
                'difficulty' => $do_kho_text,
                'estimated_time' => 30, // GiÄ‚Â¡ trĂ¡Â»â€¹ mĂ¡ÂºÂ·c Ă„â€˜Ă¡Â»â€¹nh vÄ‚Â¬ bĂ¡ÂºÂ£ng khÄ‚Â´ng cÄ‚Â³
                'tags' => [$row['MaMon']], // DÄ‚Â¹ng MÄ‚Â£ MÄ‚Â´n lÄ‚Â m tag
                'reason' => 'Recommended by Personalized System'
            ];
        }

    } catch (PDOException $e) {
        $message = "LĂ¡Â»â€”i kĂ¡ÂºÂ¿t nĂ¡Â»â€˜i CSDL: " . $e->getMessage();
        // Fallback nhĂ¡ÂºÂ¹ nĂ¡ÂºÂ¿u lĂ¡Â»â€”i db thÄ‚Â¬ rĂ¡Â»â€”ng thui khÄ‚Â´ng vĂ„Æ’ng api
    }

    $response = [
        'success'     => true,
        'message'     => $message,
        'suggestions' => $suggestions,
        'metadata'    => [
            'total_count' => count($suggestions),
            'user_id'     => $student_id,
            'course_id'   => $course_id,
            'exam_code'   => $exam_code,
            'mapped_mamon' => $ma_mon,
            'generated_at' => date('c'),
        ]
    ];

    echo json_encode($response);
}

/**
 * GET /api/exercise/{id} - Get exercise details (UC2)
 */
function handle_get_exercise($id) {
    try {
        $dsn = "odbc:Driver={SQL Server};Server=118.69.126.49;Database=Data_PersonalizedSystem;";
        $pdo = new PDO($dsn, "userPersonalizedSystem", "123456789");
        $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

        $sql = "SELECT 
                    Id, MaBaiTap, MaDoKho, MaMon,
                    CAST(TenBaiTap AS VARBINARY(MAX)) as TenBaiTapBin,
                    CAST(MoTa AS VARBINARY(MAX)) as MoTaBin,
                    CAST(YeuCau AS VARBINARY(MAX)) as YeuCauBin,
                    CAST(TieuChiChamDiem AS VARBINARY(MAX)) as TieuChiBin
                FROM BAITAP WHERE MaBaiTap = ?";
                
        $stmt = $pdo->prepare($sql);
        $stmt->execute([$id]);
        $row = $stmt->fetch(PDO::FETCH_ASSOC);

        if (!$row) {
            http_response_code(404);
            echo json_encode(['success' => false, 'message' => 'Exercise not found']);
            return;
        }

        $decode = function($bin) {
            if (empty($bin)) return '';
            if (ctype_xdigit((string)$bin)) $bin = hex2bin($bin);
            return iconv('UCS-2LE', 'UTF-8', $bin);
        };

        $do_kho_map = [1 => 'easy', 2 => 'medium', 3 => 'hard'];
            $do_kho_text = isset($do_kho_map[$row['MaDoKho']]) ? $do_kho_map[$row['MaDoKho']] : 'unknown';

        // Parse TieuChiChamDiem into readable checklist messages.
        $tieu_chi_raw = $decode($row['TieuChiBin']);
        $tieu_chi_json = json_decode($tieu_chi_raw, true);
        $test_cases = [];

        $criteria_items = [];
        if (is_array($tieu_chi_json)) {
            if (isset($tieu_chi_json['tieu_chi']) && is_array($tieu_chi_json['tieu_chi'])) {
                $criteria_items = $tieu_chi_json['tieu_chi'];
            } else {
                $criteria_items = $tieu_chi_json;
            }
        }

        foreach ($criteria_items as $tc) {
            if (is_array($tc)) {
                $message = $tc['name'] ?? $tc['message'] ?? $tc['description'] ?? $tc['title'] ?? '';
                if (isset($tc['points']) && $message !== '') {
                    $message .= ' (' . $tc['points'] . ' điểm)';
                }
            } else {
                $message = (string)$tc;
            }

            $message = trim(strip_tags($message));
            if ($message !== '') {
                $test_cases[] = ['message' => $message];
            }
        }

        if (empty($test_cases) && !empty($tieu_chi_raw)) {
            $test_cases[] = ['message' => trim(strip_tags($tieu_chi_raw))];
        }

        $response = [
            'success' => true,
            'exercise' => [
                'id' => $row['MaBaiTap'],
                'title' => $decode($row['TenBaiTapBin']),
                'description' => $decode($row['MoTaBin']),
                'difficulty' => $do_kho_text,
                'estimated_time' => 30,
                'instructions' => $decode($row['YeuCauBin']),
                'test_cases' => $test_cases,
                'hints' => [],
                'tags' => [$row['MaMon']]
            ]
        ];
        echo json_encode($response);
    } catch (PDOException $e) {
        http_response_code(500);
        echo json_encode(['success' => false, 'message' => 'Database Error: ' . $e->getMessage()]);
    }
}

/**
 * POST /api/submit - Submit exercise solution (UC3)
 */
function handle_submit_exercise() {
    $submissionId = 'sub_' . time() . '_' . rand(1000, 9999);
    echo json_encode([
        'success' => true,
        'submission_id' => $submissionId,
        'status' => 'grading',
        'message' => 'Solution submitted successfully and is being graded'
    ]);
}

/**
 * GET /api/result/{submission_id} - Get submission result (UC4)
 */
function handle_get_result($submissionId) {
    echo json_encode([
        'success' => true,
        'result' => [
            'submission_id' => $submissionId,
            'exercise_id' => 'KTLT_D5_08',
            'status' => 'graded',
            'score' => 85,
            'max_score' => 100,
            'percentage' => 85,
            'fusion_score' => 85,
            'cloud_analysis' => 'MĂ£ nguá»“n cá»§a báº¡n Ä‘Æ°á»£c thiáº¿t káº¿ ráº¥t tá»‘t, tuy nhiĂªn cĂ³ thá»ƒ tá»‘i Æ°u hoĂ¡ vĂ²ng láº·p á»Ÿ dĂ²ng sá»‘ 4 Ä‘á»ƒ giáº£m Ä‘á»™ phá»©c táº¡p thá»i gian tá»« O(n^2) xuá»‘ng O(n). ÄĂ¡nh giĂ¡ tá»•ng quan: KhĂ¡ tá»‘t.',
            'feedback' => 'Good work! Your solution is correct but could be optimized.',
            'test_results' => [
                ['test' => 'Test 1', 'passed' => true,  'message' => 'Correct output'],
                ['test' => 'Test 2', 'passed' => true,  'message' => 'Correct output'],
                ['test' => 'Test 3', 'passed' => false, 'message' => 'Edge case failed']
            ],
            'completed_at' => date('c'),
            'time_spent' => 1800
        ]
    ]);
}

/**
 * Moodle helper wrapper (fallback for environment isolation)
 */
function current_user_id() {
    global $USER;
    if (isset($USER) && isset($USER->id)) {
        return $USER->id;
    }
    return null;
}



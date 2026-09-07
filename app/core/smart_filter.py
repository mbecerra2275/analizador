# app/core/smart_filter.py
import re
from typing import List, Tuple, Dict

class SmartFilter:
    FALSE_POSITIVE_PATTERNS = [
        {'pattern': r'simularCreditoCAT1.*Response CAT1', 'type': 'SIMULATION_RESULT'},
        {'pattern': r'Response CAT1 : SimulacionModel.*mensajeError=OK', 'type': 'SIMULATION_SUCCESS'},
        {'pattern': r'EVENT SUCCESS.*sendLeakage', 'type': 'SUCCESS_EVENT'},
        {'pattern': r'executeKafka.*exito', 'type': 'KAFKA_SUCCESS'},
        {'pattern': r'Simulation service exitoso', 'type': 'SIMULATION_COMPLETE'},
        {'pattern': r'El servicio respondió correctamente', 'type': 'SERVICE_SUCCESS'},
        {'pattern': r'exito', 'type': 'GENERIC_SUCCESS'}
    ]
    
    TRUE_ERROR_PATTERNS = [
        {'pattern': r'NullPointerException', 'type': 'NULL_POINTER', 'severity': 'CRITICAL'},
        {'pattern': r'Read timed out.*elastic-apm-server-reporter', 'type': 'APM_TIMEOUT', 'severity': 'HIGH'},
        {'pattern': r'Connection refused', 'type': 'CONNECTION_REFUSED', 'severity': 'HIGH'},
        {'pattern': r'Estado de tarjeta.*[^0]', 'type': 'CARD_STATUS_ERROR', 'severity': 'MEDIUM'},
        {'pattern': r'KeycloakServiceImpl.*error getToken', 'type': 'KEYCLOAK_AUTH_ERROR', 'severity': 'CRITICAL'},
        {'pattern': r'Estado clave incorrecta', 'type': 'INVALID_CREDENTIALS', 'severity': 'HIGH'},
        {'pattern': r'validaPin.*400', 'type': 'PIN_VALIDATION_ERROR', 'severity': 'MEDIUM'},
        {'pattern': r'error_valida_captcha.*400', 'type': 'CAPTCHA_ERROR', 'severity': 'MEDIUM'},
        {'pattern': r'HttpClientErrorException', 'type': 'HTTP_CLIENT_ERROR', 'severity': 'HIGH'}
    ]
    
    @classmethod
    def classify(cls, group) -> Tuple[List[Dict], List[Dict]]:
        true_errors = []
        false_positives = []
        seen_messages = set()
        
        if group.successful:
            for entry in group.get_errors():
                # Evitar duplicados exactos
                msg_key = entry.message[:100].strip()
                if msg_key in seen_messages:
                    continue
                seen_messages.add(msg_key)
                
                is_true = False
                for pattern in cls.TRUE_ERROR_PATTERNS:
                    if re.search(pattern['pattern'], entry.message, re.IGNORECASE):
                        true_errors.append({
                            'entry': entry,
                            'type': pattern['type'],
                            'severity': pattern['severity'],
                            'reason': f'Error real: {pattern["type"]}'
                        })
                        is_true = True
                        break
                
                if not is_true:
                    is_false = False
                    for pattern in cls.FALSE_POSITIVE_PATTERNS:
                        if re.search(pattern['pattern'], entry.message, re.IGNORECASE):
                            false_positives.append({
                                'entry': entry,
                                'type': pattern['type'],
                                'reason': 'Falso positivo detectado'
                            })
                            is_false = True
                            break
                    
                    if not is_false:
                        true_errors.append({
                            'entry': entry,
                            'type': 'UNKNOWN_ERROR',
                            'severity': 'UNKNOWN',
                            'reason': 'Error no clasificado'
                        })
        else:
            for entry in group.get_errors():
                msg_key = entry.message[:100].strip()
                if msg_key in seen_messages:
                    continue
                seen_messages.add(msg_key)
                
                true_errors.append({
                    'entry': entry,
                    'type': 'TRANSACTION_FAILURE',
                    'severity': 'HIGH',
                    'reason': 'Transacción fallida'
                })
        
        return true_errors, false_positives
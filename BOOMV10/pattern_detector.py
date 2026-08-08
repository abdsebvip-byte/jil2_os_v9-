import numpy as np
import pandas as pd
from scipy.signal import argrelextrema

class PatternDetector:
    def __init__(self, data: pd.DataFrame, order=5):
        # Drop rows with NaN or missing data
        self.data = data.dropna().copy()
        self.order = order
        
    def _find_extrema(self):
        highs = self.data['High'].values
        max_idx = argrelextrema(highs, np.greater, order=self.order)[0]
        
        lows = self.data['Low'].values
        min_idx = argrelextrema(lows, np.less, order=self.order)[0]
        
        return max_idx, min_idx

    def _calc_slope(self, x, y):
        if len(x) < 2: return 0.0, 0.0
        coeffs = np.polyfit(x, y, 1)
        return coeffs[0], coeffs[1] # slope, intercept
        
    def _get_line_coords(self, x_indices, slope, intercept):
        if len(x_indices) < 2: return []
        start_idx = x_indices[0]
        end_idx = len(self.data) - 1 # Draw to the end of the chart
        
        # We need the timestamps to pass to lightweight-charts
        start_time = int(self.data.index[start_idx].timestamp())
        end_time = int(self.data.index[end_idx].timestamp())
        
        start_price = (slope * start_idx) + intercept
        end_price = (slope * end_idx) + intercept
        
        return [
            {"time": start_time, "value": start_price},
            {"time": end_time, "value": end_price}
        ]

    def detect_bull_flag(self, recent_max, recent_min, slope_high, int_high, slope_low, int_low):
        if slope_high < -0.001 and slope_low < -0.001:
            diff = abs(slope_high - slope_low)
            if diff < abs(slope_high) * 0.5:
                pole_start = max(0, recent_max[0] - 10)
                pole_rise = self.data['Close'].iloc[recent_max[0]] / self.data['Close'].iloc[pole_start] - 1
                if pole_rise > 0.05:
                    prob = min(95.0, 60.0 + (pole_rise * 100))
                    return {
                        "pattern": "علم صاعد (Bull Flag)", 
                        "type": "BULLISH", 
                        "probability": round(prob, 1), 
                        "details": "انفجار قوي متبوع بتجميع هابط صحي.",
                        "lines": {
                            "resistance": self._get_line_coords(recent_max, slope_high, int_high),
                            "support": self._get_line_coords(recent_min, slope_low, int_low)
                        }
                    }
        return None

    def detect_symmetrical_triangle(self, recent_max, recent_min, slope_high, int_high, slope_low, int_low):
        if slope_high < -0.001 and slope_low > 0.001:
            return {
                "pattern": "مثلث متماثل (Symmetrical Triangle)", 
                "type": "NEUTRAL", 
                "probability": 65.0, 
                "details": "السعر ينضغط، استعد لكسر عنيف في أحد الاتجاهين.",
                "lines": {
                    "resistance": self._get_line_coords(recent_max, slope_high, int_high),
                    "support": self._get_line_coords(recent_min, slope_low, int_low)
                }
            }
        return None

    def detect_descending_channel(self, recent_max, recent_min, slope_high, int_high, slope_low, int_low):
        if slope_high < -0.002 and slope_low < -0.002:
            if abs(slope_high - slope_low) < 0.005:
                return {
                    "pattern": "قناة هابطة (Descending Channel)", 
                    "type": "BEARISH", 
                    "probability": 70.0, 
                    "details": "السهم يتداول داخل مسار هابط منتظم.",
                    "lines": {
                        "resistance": self._get_line_coords(recent_max, slope_high, int_high),
                        "support": self._get_line_coords(recent_min, slope_low, int_low)
                    }
                }
        return None

    def detect_ascending_channel(self, recent_max, recent_min, slope_high, int_high, slope_low, int_low):
        if slope_high > 0.002 and slope_low > 0.002:
            if abs(slope_high - slope_low) < 0.005:
                return {
                    "pattern": "قناة صاعدة (Ascending Channel)", 
                    "type": "BULLISH", 
                    "probability": 75.0, 
                    "details": "مسار صاعد إيجابي قوي، راقب سقف القناة.",
                    "lines": {
                        "resistance": self._get_line_coords(recent_max, slope_high, int_high),
                        "support": self._get_line_coords(recent_min, slope_low, int_low)
                    }
                }
        return None

    def detect_head_and_shoulders(self, max_idx, min_idx):
        if len(max_idx) < 3 or len(min_idx) < 2: return None
        
        # Check last 3 peaks
        p1 = max_idx[-3]; p2 = max_idx[-2]; p3 = max_idx[-1]
        y1 = self.data['High'].iloc[p1]
        y2 = self.data['High'].iloc[p2]
        y3 = self.data['High'].iloc[p3]
        
        # Head must be highest
        if y2 > y1 and y2 > y3:
            # Shoulders roughly equal (within 2%)
            if abs(y1 - y3) / y1 < 0.02:
                # Find valleys between peaks
                valleys = [v for v in min_idx if v > p1 and v < p3]
                if len(valleys) >= 2:
                    v1 = valleys[0]; v2 = valleys[-1]
                    vy1 = self.data['Low'].iloc[v1]
                    vy2 = self.data['Low'].iloc[v2]
                    
                    # Neckline slope
                    slope, intercept = self._calc_slope([v1, v2], [vy1, vy2])
                    
                    # Check if price has broken neckline (optional for confirmation, but we detect formation)
                    return {
                        "pattern": "رأس وكتفين (Head & Shoulders)", 
                        "type": "BEARISH", 
                        "probability": 85.0, 
                        "details": "نموذج انعكاسي هبوطي قوي جداً. راقب خط العنق الأحمر (Neckline).",
                        "lines": {
                            "resistance": [],
                            "support": self._get_line_coords([v1, v2], slope, intercept)
                        }
                    }
        return None

    def detect_double_top(self, max_idx, min_idx):
        if len(max_idx) < 2 or len(min_idx) < 1: return None
        p1 = max_idx[-2]; p2 = max_idx[-1]
        y1 = self.data['High'].iloc[p1]; y2 = self.data['High'].iloc[p2]
        
        if abs(y1 - y2) / y1 < 0.015: # Within 1.5% height
            valleys = [v for v in min_idx if v > p1 and v < p2]
            if valleys:
                v1 = valleys[0]
                vy1 = self.data['Low'].iloc[v1]
                # Horizontal neckline
                slope = 0
                intercept = vy1
                return {
                    "pattern": "قمة مزدوجة (Double Top)", 
                    "type": "BEARISH", 
                    "probability": 80.0, 
                    "details": "اصطدام عنيف بالمقاومة مرتين. كسر خط العنق (الأحمر) يؤكد الهبوط.",
                    "lines": {
                        "resistance": self._get_line_coords([p1, p2], 0, y1),
                        "support": self._get_line_coords([p1, p2], 0, vy1)
                    }
                }
        return None

    def detect_double_bottom(self, max_idx, min_idx):
        if len(min_idx) < 2 or len(max_idx) < 1: return None
        v1 = min_idx[-2]; v2 = min_idx[-1]
        vy1 = self.data['Low'].iloc[v1]; vy2 = self.data['Low'].iloc[v2]
        
        if abs(vy1 - vy2) / vy1 < 0.015: # Within 1.5% height
            peaks = [p for p in max_idx if p > v1 and p < v2]
            if peaks:
                p1 = peaks[0]
                y1 = self.data['High'].iloc[p1]
                return {
                    "pattern": "قاع مزدوج (Double Bottom)", 
                    "type": "BULLISH", 
                    "probability": 80.0, 
                    "details": "تأسيس دعم قوي مرتين. اختراق خط العنق (الأخضر) يؤكد الانطلاقة.",
                    "lines": {
                        "resistance": self._get_line_coords([v1, v2], 0, y1),
                        "support": self._get_line_coords([v1, v2], 0, vy1)
                    }
                }
        return None

    def detect_patterns(self):
        max_idx, min_idx = self._find_extrema()
        
        recent_max = max_idx[-4:] if len(max_idx) >= 4 else max_idx
        recent_min = min_idx[-4:] if len(min_idx) >= 4 else min_idx
        
        if len(recent_max) < 2 or len(recent_min) < 2:
            return None
            
        highs_y = self.data['High'].iloc[recent_max].values
        lows_y = self.data['Low'].iloc[recent_min].values
        
        slope_high, int_high = self._calc_slope(recent_max, highs_y)
        slope_low, int_low = self._calc_slope(recent_min, lows_y)

        # فحص النماذج بالترتيب من الأقوى للأضعف
        
        hs = self.detect_head_and_shoulders(max_idx, min_idx)
        if hs: return hs
        
        dt = self.detect_double_top(max_idx, min_idx)
        if dt: return dt
        
        db = self.detect_double_bottom(max_idx, min_idx)
        if db: return db

        flag = self.detect_bull_flag(recent_max, recent_min, slope_high, int_high, slope_low, int_low)
        if flag: return flag
        
        asc_channel = self.detect_ascending_channel(recent_max, recent_min, slope_high, int_high, slope_low, int_low)
        if asc_channel: return asc_channel
        
        desc_channel = self.detect_descending_channel(recent_max, recent_min, slope_high, int_high, slope_low, int_low)
        if desc_channel: return desc_channel
        
        triangle = self.detect_symmetrical_triangle(recent_max, recent_min, slope_high, int_high, slope_low, int_low)
        if triangle: return triangle
        
        return None

import numpy as np
from scipy.signal import savgol_filter


class ApexSmoother:

    # Panjang window = 3% panjang sinyal (ganjil), minimal 5 frame.
    #
    # Riwayat (audit 2026-10-09, lihat report/findings/audit-spotting-casme2.md):
    #   - desain asli notebook: 5% panjang sinyal, clamp 31 (varian Casme/v2)
    #     dan window tetap 28 (varian pertama micro_expression_spotting.ipynb)
    #   - pernah diubah jadi TETAP 7 frame -> regresi (F1 0,214 vs 0,260)
    #   - disapu ulang pada 86 video CAS(ME)^2: 3% adaptif paling baik dan
    #     konsisten di validasi split subjek (F1 test 0,315-0,320 vs 0,213).
    # 3% adaptif dipilih daripada window tetap karena ikut menyesuaikan panjang
    # video (60 fps vs 30 fps, segmen pendek vs panjang).
    WINDOW_LENGTH_PERCENTAGE = 0.03
    MIN_WINDOW_LENGTH = 5

    @staticmethod
    def calculate_window_length(length: int) -> int:
        """
        Menghitung panjang window smoothing: 3% panjang sinyal (ganjil),
        minimal MIN_WINDOW_LENGTH, dan selalu lebih kecil dari panjang sinyal
        (syarat savgol_filter).
        """
        window_length = int(length * ApexSmoother.WINDOW_LENGTH_PERCENTAGE)

        # savgol_filter memerlukan panjang window ganjil
        if window_length % 2 == 0:
            window_length += 1

        window_length = max(ApexSmoother.MIN_WINDOW_LENGTH, window_length)

        # Jaga window tetap lebih kecil dari sinyal (kalau tidak, savgol error)
        if window_length >= length:
            window_length = length - 1 if length % 2 == 0 else length - 2

        return window_length


    @staticmethod
    def calculate_polyorder(window_length: int) -> int:
        """
        Menghitung orde polinomial yang sesuai untuk savgol filter berdasarkan panjang window.

        Args:
            window_length (int): Panjang window yang digunakan untuk perataan.

        Returns:
            int: Orde polinomial yang digunakan dalam savgol filter.
        """

        match window_length:
            case wl if wl <= 7:
                return 2
            case wl if wl <= 15:
                return 3
            case _:
                return 4


    @staticmethod
    def smooth(signal: list) -> list:
        """
        Melakukan perataan sinyal menggunakan Savitzky-Golay filter
        dengan parameter window dan polyorder yang dihitung secara adaptif.

        Args:
            signal (list): Sinyal input yang akan diratakan.

        Returns:
            list: Sinyal yang sudah diratakan.

        Raises:
            ValueError: Jika sinyal terlalu pendek untuk di-smooth.
        """
        length = len(signal)
        window_length = ApexSmoother.calculate_window_length(length)
        polyorder = ApexSmoother.calculate_polyorder(window_length)

        if window_length >= length:
            raise ValueError(
                f"Sinyal terlalu pendek ({length} sampel) untuk di-smooth "
                f"(window_length={window_length})"
            )

        smoothed = savgol_filter(signal, window_length=window_length, polyorder=polyorder)
        return smoothed.tolist()

import { Button } from "@/components/ui/button";
import { DialogFooter } from "@/components/ui/dialog";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

type ModalFooterProps = {
  loadingSave: boolean;
  isFormValid: boolean;
  editingId: string | null;
  handleSave: () => void;
  handleCloseModal: () => void;
  disabledReason: string | null;
};

const ModalFooter = ({
  loadingSave,
  isFormValid,
  editingId,
  handleSave,
  handleCloseModal,
  disabledReason,
}: ModalFooterProps) => {
  const isDisabled = loadingSave || !isFormValid;
  const buttonLabel = loadingSave
    ? "Salvando..."
    : editingId
      ? "Salvar Alterações"
      : "Salvar";

  return (
    <DialogFooter>
      <Button
        variant="outline"
        className="cursor-pointer"
        onClick={handleCloseModal}
      >
        Cancelar
      </Button>
      {disabledReason ? (
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <span className="inline-flex w-full sm:w-auto">
                <Button
                  className="pointer-events-none w-full sm:w-auto mb-2 sm:mb-0"
                  disabled
                >
                  {buttonLabel}
                </Button>
              </span>
            </TooltipTrigger>
            <TooltipContent side="top">
              <p>{disabledReason}</p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      ) : (
        <Button
          className="cursor-pointer mb-2 sm:mb-0"
          onClick={handleSave}
          disabled={isDisabled}
        >
          {buttonLabel}
        </Button>
      )}
    </DialogFooter>
  );
};

export default ModalFooter;

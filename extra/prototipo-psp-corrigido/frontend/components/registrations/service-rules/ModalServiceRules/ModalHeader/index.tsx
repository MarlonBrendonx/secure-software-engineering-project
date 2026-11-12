import {
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

type ModalHeaderProps = {
  editingId: string | null;
};

const ModalHeader = ({ editingId }: ModalHeaderProps) => {
  return (
    <DialogHeader>
      <DialogTitle>
        {editingId ? "Editar Serviço e Regras" : "Novo Serviço e Regras"}
      </DialogTitle>
      <DialogDescription>
        {editingId
          ? "Altere os dados do serviço e suas regras de faturamento"
          : "Preencha os dados para cadastrar um novo serviço e regras"}
      </DialogDescription>
    </DialogHeader>
  );
};

export default ModalHeader;
